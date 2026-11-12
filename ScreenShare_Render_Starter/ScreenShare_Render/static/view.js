const statusEl=document.getElementById("status"), video=document.getElementById("screen");
const requestId=location.pathname.split("/").pop();
let socket=null,pc=null;
async function start(){
 const c=await (await fetch("/api/config")).json();
 pc=new RTCPeerConnection({iceServers:c.ice_servers});
 pc.addTransceiver("video",{direction:"recvonly"});
 pc.ontrack=e=>{video.srcObject=e.streams[0];statusEl.textContent="Receiving live screen.";};
 pc.onconnectionstatechange=()=>{statusEl.textContent="Connection: "+pc.connectionState};
 socket=new WebSocket(`${location.protocol==="https:"?"wss":"ws"}://${location.host}/ws/${encodeURIComponent(requestId)}/viewer`);
 socket.onmessage=async ev=>{
  const m=JSON.parse(ev.data);
  if(m.type==="peer_joined")statusEl.textContent="Connected. Waiting for the owner to start sharing.";
  if(m.type==="offer"){
   await pc.setRemoteDescription({type:"offer",sdp:m.sdp});
   const answer=await pc.createAnswer();await pc.setLocalDescription(answer);
   await new Promise(resolve=>{
    if(pc.iceGatheringState==="complete")return resolve();
    const f=()=>{if(pc.iceGatheringState==="complete"){pc.removeEventListener("icegatheringstatechange",f);resolve()}};
    pc.addEventListener("icegatheringstatechange",f);
   });
   socket.send(JSON.stringify({type:"answer",sdp:pc.localDescription.sdp}));
  }
  if(m.type==="stop")statusEl.textContent="The owner stopped sharing.";
  if(m.type==="peer_disconnected")statusEl.textContent="The owner disconnected.";
 };
 socket.onopen=()=>statusEl.textContent="Viewer connected. Waiting for the screen owner.";
}
start().catch(e=>statusEl.textContent="Connection error: "+e.message);
