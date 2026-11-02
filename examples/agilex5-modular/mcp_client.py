"""Repository programmer adapter: native Quartus CLI or an explicitly configured MCP.

Only callers holding the shared hardware mutex may query/program the board.
CLI evidence is labelled as CLI; it is never presented as a vendor MCP reply.
"""
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import threading
import time
import uuid

from bench import ROOT, BenchError, checked_container, container_command
from owned_process import OwnedContainerProcess


def describe_chain(raw):
    lines = []
    device = 0
    for line in raw.splitlines():
        cable = re.match(r'^(\d+)\)\s+(.+)$', line)
        if cable:
            lines.append(f'  {cable[1]}: {cable[2]}')
            device = 0
        else:
            found = re.match(r'^\s+([0-9a-fA-F]{8})\s+(.+)$', line)
            if found:
                device += 1
                lines.append(f'    Device {device}: JTAG ID 0x{found[1]} ({found[2]})')
    if not lines:
        raise BenchError('No JTAG cables found; check vendor drivers, cable ownership and jtagconfig')
    return '\n'.join(lines)


class MCP:
    def __init__(self, kind):
        if kind != 'programmer':
            raise ValueError('This adapter supports the programmer only')
        self.jobs = {}
        self.process = None
        self.sequence = 0
        command = os.environ.get('AGILEX_PROGRAMMER_MCP_COMMAND')
        self.backend = 'vendor-mcp' if command else 'quartus-cli'
        if command:
            argv = json.loads(command)
            if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
                raise BenchError('AGILEX_PROGRAMMER_MCP_COMMAND must be a JSON argv array')
            self.messages = queue.Queue()
            invocation=container_command(argv)
            if os.environ.get('AGILEX_EXECUTION') != 'native':invocation.insert(2,'-i')
            self.process = subprocess.Popen(invocation, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, text=True)
            def read():
                for line in self.process.stdout:
                    try: self.messages.put(json.loads(line))
                    except ValueError: pass
            threading.Thread(target=read, daemon=True).start()
            try:
                self.request('initialize', {'protocolVersion':'2024-11-05', 'capabilities':{},
                    'clientInfo':{'name':'agilex-lab','version':'1'}})
                self.send({'jsonrpc':'2.0','method':'notifications/initialized'})
            except BaseException:
                self.close()
                raise

    def send(self, message):
        self.process.stdin.write(json.dumps(message)+'\n')
        self.process.stdin.flush()

    def request(self, method, arguments, timeout=30):
        self.sequence += 1
        identifier = self.sequence
        self.send({'jsonrpc':'2.0','id':identifier,'method':method,'params':arguments})
        deadline = time.monotonic()+timeout
        while time.monotonic() < deadline:
            try: message = self.messages.get(timeout=.2)
            except queue.Empty:
                if self.process.poll() is not None: raise BenchError('Programmer MCP exited')
                continue
            if message.get('id') == identifier:
                if 'error' in message: raise BenchError(str(message['error']))
                return message['result']
        raise BenchError('Programmer MCP timed out; inspect its connection before retrying')

    def call(self, name, arguments):
        if self.process is not None:
            reply = self.request('tools/call', {'name':name,'arguments':arguments})
            if reply.get('isError'): raise BenchError(str(reply))
            if 'structuredContent' in reply: return reply['structuredContent']
            text = '\n'.join(item.get('text','') for item in reply.get('content',[]))
            try: return json.loads(text)
            except ValueError: return {'text':text,'backend':self.backend}
        if name == 'read_jtag_config':
            raw = checked_container(['jtagconfig'],timeout=30)
            return {'text':describe_chain(raw),'raw':raw,'backend':self.backend}
        if name == 'read_config_status':
            args = ['quartus_pgm','-m','jtag','-c',arguments['cable'],
                    '--device='+str(arguments['device_index']),'--status']
            return {'text':checked_container(args,timeout=30),'backend':self.backend}
        if name == 'program_sram_device':
            job = uuid.uuid4().hex
            folder = ROOT/'build/programmer-jobs'
            folder.mkdir(parents=True,exist_ok=True)
            log = (folder/(job+'.log')).open('w')
            args = ['timeout','--kill-after=5s','180s','quartus_pgm','-m','jtag',
                    '-c',arguments['cable'],'-o',
                    'p;'+arguments['file_path']+'@'+str(arguments['device_index'])]
            try: process = OwnedContainerProcess(args,stdout=log,stderr=subprocess.STDOUT)
            except BaseException:
                log.close()
                raise
            self.jobs[job] = (process,log)
            return {'jobId':job,'projectDir':str(folder),'backend':self.backend}
        if name == 'get_job_status':
            process, log = self.jobs[arguments['jobId']]
            code = process.poll()
            if code is not None:
                process.close()
                log.close()
            return {'status':'running' if code is None else ('completed' if code == 0 else 'failed'),
                    'exitCode':code,'backend':self.backend}
        raise BenchError('Unsupported programmer operation: '+name)

    def close(self):
        for process, log in self.jobs.values():
            process.close()
            log.close()
        if self.process is not None:
            self.process.stdin.close()
            try: self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                try: self.process.wait(timeout=5)
                except subprocess.TimeoutExpired: self.process.kill(); self.process.wait()
