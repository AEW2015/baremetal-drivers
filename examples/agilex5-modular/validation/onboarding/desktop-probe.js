const vscode=require('vscode');const fs=require('fs');const path=require('path');
const root='/tmp/agx-vscode-check';
function record(type,data){fs.appendFileSync(path.join(root,'events.jsonl'),JSON.stringify({time:new Date().toISOString(),type,...data})+'\n');}
exports.activate=function(ctx){
 record('activated',{});
 vscode.debug.registerDebugAdapterTrackerFactory('cppdbg',{createDebugAdapterTracker(session){
  return {onDidSendMessage:async m=>{
   if(m.type==='event'&&m.event==='stopped'){
    try{
     const frames=await session.customRequest('stackTrace',{threadId:m.body.threadId,startFrame:0,levels:5});
     const frame=frames.stackFrames[0];record('stopped',{session:session.name,reason:m.body.reason,threadId:m.body.threadId,frame});
     await vscode.window.showTextDocument(vscode.Uri.file(frame.source.path),{selection:new vscode.Range(frame.line-1,0,frame.line-1,0)});
     if(session.name.startsWith('QEMU')&&frame.name.includes('qemu_done')){
      for(const expression of ['failures','vector_result','source[511] == destination[511]']){
       const v=await session.customRequest('evaluate',{expression,frameId:frame.id,context:'watch'});record('evaluate',{expression,...v});
      }
     }
    }catch(e){record('error',{error:String(e)});}
   }
   if(m.type==='event'&&['terminated','exited'].includes(m.event))record(m.event,{body:m.body,session:session.name});
  },onError:e=>record('adapter_error',{error:String(e)}),onExit:(code,signal)=>record('adapter_exit',{code,signal,session:session.name})};
 }});
 vscode.debug.onDidStartDebugSession(s=>record('started',{session:s.name}));
 vscode.debug.onDidTerminateDebugSession(s=>record('session_ended',{session:s.name}));
 const folder=vscode.workspace.workspaceFolders[0];
 if(folder){const source=vscode.Uri.joinPath(folder.uri,'qemu/hello.c');vscode.debug.addBreakpoints([new vscode.SourceBreakpoint(new vscode.Location(source,new vscode.Position(12,0)))]);}
};
