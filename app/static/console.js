"use strict";
const $ = (id) => document.getElementById(id);
const sceneNames = {S0:"Início", S1:"Cardápio", S2:"Detalhes", S3:"Revisão", S4:"Confirmação", S5:"Ajuda"};
let current, timer, busy=false, events=[];
const reserved = new URLSearchParams(location.search).get("reservado")==="1";
const phone=$("phone"), surface=$("surface"), footer=$("footer"), lens=$("lens"), inner=$("lens-inner");
function stop(){ clearInterval(timer); timer=null; $("play").textContent="Reproduzir"; }
function selectMode() {
  const mode=$("mode").value;
  $("zoom-label").hidden=mode!=="R";
  $("seed-label").hidden=mode==="manual";
  for(const option of $("task").options){
    option.disabled=mode!=="manual" && !["C1","C2"].includes(option.value);
  }
  if($("task").selectedOptions[0].disabled) $("task").value="C1";
}
if(reserved) for(const [code,title] of [["V1","Jantar para dois"],["V2","Último pedido"]])
  $("task").add(new Option(code+" · "+title,code));
$("mode").onchange=selectMode;
selectMode();
async function request(path, payload){
  const r=await fetch(path,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
  const body=await r.json();
  if(!r.ok) throw Error(body.error || "Falha ao atualizar a sessão.");
  return body;
}
function escapeFocus(id){return [...surface.children,...footer.children].find(e=>e.dataset.sign===id);}
function sign(e, isLens, fixed=false){
  const manual=!isLens && current.mode==="manual";
  const receipt=!isLens && current.done && current.scene==="S4" && e.action==="help";
  const interactive=receipt || (manual && !!e.action);
  const el=document.createElement(interactive?"button":"div");
  el.className="sign "+e.style+(interactive?" tap":"");
  el.dataset.sign=e.id;
  const [x,y,w,h]=e.box;
  el.style.left=(100*x/360)+"%";el.style.width=(100*w/360)+"%";
  el.style.top=(fixed ? y-current.scroll-800 : y)+"px"; el.style.height=h+"px";
  const lines=document.createElement("span");lines.className="lines";
  for (const l of e.text_lines ?? [{text:e.text}]) {
    const line=document.createElement("span"); line.className="line";line.textContent=l.text;lines.append(line);
  }
  el.append(lines);
  if(interactive){
    el.type="button";el.onclick=receipt?()=>showReceiptHelp("help"):()=>act(e.action);
    if(e.part && e.part!=="name" && e.action.startsWith("open:")) el.tabIndex=-1;
    if(e.selected!==undefined) el.setAttribute("aria-pressed",String(e.selected));
    if(e.action.startsWith("open:") && e.part==="name")el.setAttribute("aria-label","Consultar "+e.text);
    if(["+","−","Alterar","Remover"].includes(e.text) && e.line!==undefined) {
      const name=current.elements.find(n=>n.id==="line:"+e.line)?.text ?? "";
      el.setAttribute("aria-label",({"+" : "Aumentar a quantidade de ", "−" : "Diminuir a quantidade de "}[e.text] ?? e.text+" ")+name);
    }
    if(e.action==="more" || e.action==="less") el.setAttribute("aria-label",e.action==="more"?"Aumentar quantidade":"Diminuir quantidade");
  } else if(e.role==="heading"||e.role==="name"){
    el.setAttribute("role","heading");el.setAttribute("aria-level",e.role==="heading"?"3":"4");
  }
  return el;
}
function drawLens(){
  if(!current||current.mode==="manual")return;
  const {region:r,elements}=current, scale=lens.clientWidth/r.largura;
  lens.style.height=(r.altura*scale)+"px";
  inner.replaceChildren();inner.style.height=current.height+"px";
  for(const e of elements)if(e.box[1]+e.box[3]>=r.y && e.box[1]<=r.y+r.altura)inner.append(sign(e,true));
  inner.style.transform="scale("+scale+") translate("+(-r.x)+"px,"+(-r.y)+"px)";
}
function render(data, initial){
  const previous=current, focusId=document.activeElement?.dataset.sign, oldScroll=phone.scrollTop;
  current=data;
  const manual=data.mode==="manual", different=initial || previous?.scene!==data.scene;
  events=initial?data.events:[...events,...data.events];
  surface.replaceChildren();footer.replaceChildren();
  surface.style.height=data.height+"px";
  for(const e of data.elements){
    (e.fixed?footer:surface).append(sign(e,false,e.fixed));
  }
  phone.scrollTop=manual ? (different?0:oldScroll) : data.scroll;
  if(!initial && manual){
    if(different) phone.focus({preventScroll:true});
    else escapeFocus(focusId)?.focus({preventScroll:true});
  }
  $("version-info").textContent="Versão "+data.version+" · "+sceneNames[data.scene];
  $("task-info").textContent=data.task;
  $("instruction").textContent=data.instruction;
  $("quit").hidden=!manual || data.done;
  $("controls").hidden=manual;$("r-controls").hidden=data.mode!=="R";$("p-controls").hidden=data.mode!=="lens";
  $("lens-panel").hidden=manual;$("outline").hidden=manual;
  $("status").textContent="Passo "+data.step+(data.done?" · Encerrado":"");
  $("mechanism-note").textContent=data.mode==="R"?"Método de referência executado por regras.":"Gestos escolhidos pelo operador. A lente, a memória, os deslizes e o acionador de ajuda usam a configuração P.";
  for(const id of ["step","play","apply"]) $(id).disabled=data.done;
  if(!manual){
    $("factor").textContent=data.region.z.toLocaleString("pt-BR",{maximumFractionDigits:2})+"×";
    const {x,y,largura,altura}=data.region, outline=$("outline");
    outline.style.left=(100*x/360)+"%";outline.style.top=y+"px";
    outline.style.width=(100*largura/360)+"%";outline.style.height=altura+"px";
    $("projection").textContent=JSON.stringify(data.public,null,2);
    const old=$("gesture").value;
    $("gesture").replaceChildren(...(data.public?.acoes ?? []).map(a=>new Option(a,a)));
    if([ ...$("gesture").options ].some(o=>o.value===old)) $("gesture").value=old;
    drawLens();
  }
  $("trace").textContent=JSON.stringify(events.slice(-50),null,2);
  $("count").textContent=events.length+" eventos";
  $("recent").replaceChildren(...events.slice(-5).reverse().map(e=>{
    const li=document.createElement("li");const small=document.createElement("small");
    small.textContent=String(e.passo).padStart(2,"0")+" · ";li.append(small,document.createTextNode(e.tipo));return li;
  }));
  $("results").hidden=!data.metrics;
  if(data.metrics)$("metrics").textContent=JSON.stringify(data.metrics,null,2);
  if(data.done)stop();
}
async function start(){
  if(busy)return;
  stop();busy=true;$("error").textContent="";
  try {
    render(await request("/api/start",{task:$("task").value,mode:$("mode").value,version:$("version").value,
      zoom:Number($("zoom").value),seed:Number($("seed").value),reserved}),true);
  }catch(e){$("error").textContent=e.message;}finally{busy=false;}
}
async function act(action){
  if(busy||!current||current.done)return;
  busy=true;$("error").textContent="";
  try{render(await request("/api/action",{session:current.session,cursor:current.cursor,action}),false);}
  catch(e){stop();$("error").textContent=e.message;}finally{busy=false;}
}
$("settings").onsubmit=e=>{e.preventDefault();start();};
$("quit").onclick=()=>act("DESISTIR");
$("step").onclick=()=>act("");$("apply").onclick=()=>act($("gesture").value);
$("play").onclick=()=>{if(timer)stop();else{ $("play").textContent="Pausar";timer=setInterval(()=>act(""),600);act(""); }};
async function showReceiptHelp(action){
  if(busy)return;
  busy=true;
  try{
    const help=await request("/api/receipt-help",{session:current.session,action});
    const dialog=$("receipt-help");
    $("receipt-log").textContent=JSON.stringify(help.events,null,2);
    if(help.closed){dialog.close();return;}
    $("receipt-content").textContent=help.content;
    $("receipt-layers").replaceChildren(...Object.entries(help.layers).map(([key,name])=>{
      const button=document.createElement("button");button.type="button";button.textContent=name;
      button.className="secondary";button.setAttribute("aria-pressed",String(key===help.layer));
      button.onclick=()=>showReceiptHelp("layer:"+key);return button;
    }));
    if(!dialog.open) dialog.showModal();
    else dialog.querySelector('[aria-pressed="true"]').focus();
  }catch(e){$("error").textContent=e.message;}finally{busy=false;}
}
$("receipt-close").onclick=()=>showReceiptHelp("back");
$("receipt-help").addEventListener("cancel",e=>{e.preventDefault();showReceiptHelp("back");});
document.addEventListener("keydown",e=>{
  if(!current)return;
  if(current.done){
    if(e.key==="F1" && current.scene==="S4" && !$("receipt-help").open){
      e.preventDefault();showReceiptHelp("help");
    }
    return;
  }
  const action=e.key==="F1"?"help":e.key==="Escape"?"back":null;
  if(action && current.elements.some(s=>s.action===action)){
    e.preventDefault();
    if(current.mode==="manual") act(action);
    if(current.mode==="lens") act(action==="help"?"TOCAR(Ajuda)":"VOLTAR");
  }
});
new ResizeObserver(drawLens).observe(lens);
start();
