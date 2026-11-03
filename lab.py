#!/usr/bin/env python3
"""Portable entry point. Paths in local configuration are relative to the example root."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

REPO = Path(__file__).resolve().parent
LAB = REPO/'examples/agilex5-modular'
CONFIG = LAB/'build/local.json'
DEFAULTS = {'backend':'container', 'image':'agilex-learning:26.3',
            'container':'', 'container_user':'dev', 'container_root':'/work/examples/agilex5-modular',
            'bootstrap_dir':'build/boot', 'hardware_lock':'hardware.lock', 'uart':''}


def local_path(value):
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (LAB/path).resolve()


def load_config(path=CONFIG):
    values = dict(DEFAULTS)
    if path.is_file():
        data = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or set(data)-set(DEFAULTS):
            raise ValueError('Unknown local configuration fields')
        if not all(isinstance(value,str) for value in data.values()):
            raise ValueError('Local configuration values must be strings')
        values.update(data)
    if values['backend'] not in ('native','container','wsl'):
        raise ValueError('Choose native, container or wsl backend')
    return values


def tool_command(config, command):
    if config['backend'] == 'native':
        return [sys.executable,*command[1:]] if command[0]=='python3' else command
    if config['backend'] != 'container':
        raise ValueError('WSL commands are delegated before tool selection')
    if config['container']:
        return ['docker','exec','-i','-u',config['container_user'],'-w',config['container_root'],config['container'],*command]
    if ',' in str(REPO):
        raise ValueError('Docker --mount cannot represent a comma in the checkout path')
    return ['docker','run','--rm','-i','--mount',f'type=bind,src={REPO},dst=/work',
            '-w','/work/examples/agilex5-modular',config['image'],*command]


def hardware_environment(config):
    if platform.system() != 'Linux':
        raise ValueError('Run hardware automation inside Linux/WSL2; use --backend wsl on Windows')
    if config['backend']=='container' and not config['container']:
        raise ValueError('Configure an existing hardware tool container; an ephemeral learning image has no Quartus or USB access')
    environment = dict(os.environ)
    environment.update({'AGILEX_BOOTSTRAP_DIR':str(local_path(config['bootstrap_dir'])),
        'AGILEX_MCP_CLIENT':str(LAB/'mcp_client.py'),
        'AGILEX_HARDWARE_LOCK':str(local_path(config['hardware_lock'])),
        'AGILEX_UART':config['uart'],'AGILEX_FORCE_FULL_BOOT':'1',
        'AGILEX_EXECUTION':'native' if config['backend']=='native' else 'container'})
    if config['backend']=='container':
        environment.update({'AGILEX_CONTAINER':config['container'],
                            'AGILEX_CONTAINER_ROOT':config['container_root'],'AGILEX_CONTAINER_USER':config['container_user']})
    return environment


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend',choices=['native','container','wsl'])
    parser.add_argument('--container')
    parser.add_argument('--container-root')
    parser.add_argument('--container-user')
    parser.add_argument('--image')
    parser.add_argument('--bootstrap-dir')
    parser.add_argument('--hardware-lock')
    parser.add_argument('--uart')
    parser.add_argument('--dry-run',action='store_true',help='Print commands without executing tools or accessing hardware')
    sub = parser.add_subparsers(dest='action',required=True)
    sub.add_parser('configure',help='Save this checkout’s ignored build/local.json')
    sub.add_parser('paths')
    image = sub.add_parser('image',help='Build the learning image, or a user-supplied Quartus base')
    image.add_argument('--base-image')
    sub.add_parser('learning-check')
    qemu = sub.add_parser('qemu')
    qemu.add_argument('--build-only',action='store_true')
    qemu.add_argument('--experiment',action='store_true')
    qemu.add_argument('--debug',action='store_true')
    simics = sub.add_parser('simics')
    simics.add_argument('--setup',action='store_true')
    simics.add_argument('--build-only',action='store_true')
    hardware = sub.add_parser('hardware')
    hardware.add_argument('example',choices=['doctor','hello','core','pr','usb-linux'])
    hardware.add_argument('--usb-peer',help='PC IPv4 address reachable from the USB hub Ethernet network')
    hardware.add_argument('--bind',default='192.168.50.1',help='PC address on the HPS boot Ethernet network')
    hardware.add_argument('--board-ip',default='192.168.50.3')
    hardware.add_argument('--leave-linux-running',action='store_true',help='USB Linux only: leave a responsive Linux session running for hotplug')
    hardware.add_argument('--loader',choices=['jtag','hps'],default='jtag')
    hardware.add_argument('--manifest',default='build/pr/hardware-manifest.json')
    hardware.add_argument('--build',action='store_true',help='Build the current SDK and hardware Hello first')
    args = parser.parse_args(argv)
    config = load_config()
    for key in DEFAULTS:
        value = getattr(args,key,None)
        if value is not None: config[key]=value
    if args.action=='configure':
        if args.dry_run: print(json.dumps(config,indent=2));return 0
        CONFIG.parent.mkdir(parents=True,exist_ok=True)
        CONFIG.write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
        print('Saved '+str(CONFIG));return 0
    if args.action=='paths':
        print(json.dumps({'repo':str(REPO),'examples':str(LAB),'config':str(CONFIG),
              'bootstrap':str(local_path(config['bootstrap_dir'])),'configuration':config},indent=2));return 0
    if config['backend']=='wsl':
        if platform.system()!='Windows':raise ValueError('The wsl backend is for Windows; use native inside WSL')
        if args.dry_run:
            print(json.dumps({'backend':'wsl','repo':str(REPO),'action':args.action}));return 0
        mapped = subprocess.check_output(['wsl.exe','--exec','wslpath','-a','-u',str(REPO)],text=True,encoding='utf-8').strip()
        original = list(sys.argv[1:] if argv is None else argv)
        # Override the backend at the same option position, preserving all arguments.
        cleaned=[]
        skip=False
        for value in original:
            if skip:skip=False;continue
            if value=='--backend':skip=True;continue
            if value.startswith('--backend='):continue
            cleaned.append(value)
        original=['--backend','native',*cleaned]
        return subprocess.run(['wsl.exe','--cd',mapped,'--exec','python3','lab.py',*original]).returncode
    if platform.system()=='Windows' and config['backend']=='native' and args.action in ('simics','hardware','learning-check'):
        raise ValueError('Use --backend wsl for Linux shell/Simics/hardware automation on Windows; native Quartus GUI remains available')
    environment = dict(os.environ)
    commands = []
    tool = lambda command: tool_command(config,command)
    if args.action=='image':
        command=['docker','build','--build-arg','USER_UID='+str(getattr(os,'getuid',lambda:1000)()),
                 '--build-arg','USER_GID='+str(getattr(os,'getgid',lambda:1000)()),'-t',config['image']]
        if args.base_image:command+=['--build-arg','BASE_IMAGE='+args.base_image]
        commands=[command+[str(LAB/'container')]]
    elif args.action=='learning-check':commands=[tool(['bash','container/check-learning.sh'])]
    elif args.action=='qemu':
        if args.debug and config['backend']=='container' and not config['container']:
            raise ValueError('For GDB, use native/WSL or configure a running container and attach VS Code to it')
        commands=[tool(['python3','qemu/build.py'])]
        if not args.build_only:
            commands.append(tool(['python3','qemu/experiment.py'] if args.experiment else
                                 ['python3','qemu/run.py','--debug' if args.debug else '--check']))
    elif args.action=='simics':
        if config['backend']=='container' and not config['container']:
            raise ValueError('Use native/WSL Simics or configure a container with the licensed simulator installed')
        if args.setup:commands.append(tool(['python3','simics/setup.py']))
        commands.append(tool(['bash','simics/build.sh','OCRAM']))
        if not args.build_only:commands.append(tool(['python3','simics/run.py','--only','hello']))
    elif args.action=='hardware':
        environment=hardware_environment(config)
        if args.example=='doctor':commands=[[sys.executable,str(LAB/'doctor.py'),'--target','hardware']]
        elif args.example=='hello':
            if args.build:commands += [tool(['bash','simics/build.sh','DDR']),tool(['bash','hardware-candidates/build.sh'])]
            commands += [[sys.executable,str(LAB/'upstream-lab/hardware.py'),'--suite','candidates',
                          '--only','hello','--artifacts',str(LAB/'build/hardware-candidates'),
                          '--port',config['uart'],'--wait-for-hardware']]
        elif args.example=='core':commands=[[sys.executable,str(LAB/'run_suite.py'),'--only','core','--full-recovery']]
        elif args.example=='pr':commands=[[sys.executable,str(LAB/'fabric/pr/hardware/run.py'),
                    '--manifest',str(local_path(args.manifest)),'--loader',args.loader,'--port',config['uart'],'--run','--wait-for-hardware']]
        elif args.example=='usb-linux':
            if args.build:commands.append(tool(['bash','usb-linux/build.sh']))
            commands.append([sys.executable,str(LAB/'usb-linux/run.py'),'--port',config['uart'],
                             '--bind',args.bind,'--board-ip',args.board_ip])
            if args.usb_peer:commands[-1] += ['--usb-peer',args.usb_peer]
            if args.leave_linux_running:commands[-1].append('--leave-linux-running')
        if not config['uart'] and not args.dry_run:raise ValueError('Configure --uart with the verified Linux SOM UART device')
    if args.dry_run:
        print(json.dumps({'cwd':str(LAB),'commands':commands,'backend':config['backend']},indent=2));return 0
    for command in commands:
        print('Running: '+json.dumps(command),flush=True)
        result = subprocess.run(command,cwd=LAB,env=environment)
        if result.returncode:return result.returncode
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        print('ERROR: '+str(error),file=sys.stderr);raise SystemExit(2)
