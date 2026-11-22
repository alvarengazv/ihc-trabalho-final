"use strict";
const $ = (id) => document.getElementById(id);
const sceneNames = {S0:"Início", S1:"Cardápio", S2:"Detalhes", S3:"Revisão", S4:"Confirmação", S5:"Ajuda"};
let current, timer, busy=false, events=[];
const phone=$("phone"), surface=$("surface"), footer=$("footer"), lens=$("lens"), inner=$("lens-inner");
const modeNames={manual:"Interface manual", R:"Executor de referência R", lens:"Mecanismos P"};
const modeHints={
  manual:"A pessoa toca diretamente nos signos da tela simulada. Cada toque vira um evento no registro.",
  R:"O método especialista é executado por regras, passo a passo, sem modelo de linguagem.",
  lens:"O operador escolhe os gestos; a lente, a memória, os deslizes e o acionador de ajuda seguem a configuração P."
};
const errorNames={E1:"Seleção",E2:"Associação",E3:"Opção ou quantidade",E4:"Deslize motor",E5:"Discrepância na revisão",E6:"Violação de regra"};
const tileSpec=[
  ["S","Sucesso",true],["A","Ações executadas",true],["N_ref","Ações de referência"],["R_A","Razão de ações",true],
  ["U","Aberturas de ajuda"],["D","Navegação por alvo"],["V","Revisitas"],["O","Signos ausentes"]
];
let visited=new Set();
function stop(){ clearInterval(timer); timer=null; $("play").textContent="Reproduzir"; }
const number=v=>v==null?"—":typeof v==="number"?v.toLocaleString("pt-BR",{maximumFractionDigits:2}):String(v);
function eventKind(t){
  if(t==="acao_executada")return "act";
  if(t.startsWith("item_")||t==="opcao_selecionada")return "order";
  if(t==="tela_alterada")return "scene";
  if(t.startsWith("ajuda_"))return "help";
  if(["deslize_injetado","acao_rejeitada","desistencia","limite_atingido"].includes(t))return "alert";
  if(["pedido_confirmado","tarefa_encerrada"].includes(t))return "end";
  if(["observacao","elemento_visto","vista_deslocada","zoom_alterado"].includes(t))return "see";
  return "";
}
function eventDetail(e){
  const d=e.dados||{};
  switch(e.tipo){
    case "acao_executada": return [d.gesto||d.acao, d.alvo!=null && !d.gesto ? "→ "+d.alvo : "", d.origem && d.origem!=="pessoa" ? "· "+d.origem : ""].filter(Boolean).join(" ");
    case "tela_alterada": return d.categoria ? "Categoria "+d.categoria : (sceneNames[d.anterior]||d.anterior)+" → "+(sceneNames[d.nova]||d.nova);
    case "item_adicionado": case "item_alterado": case "item_removido":
      return "linha "+(d.linha+1)+" · "+(d.novo?.nome||d.anterior?.nome||"item "+d.item)+(d.quantidade!=null?" · "+d.quantidade+" un.":"");
    case "opcao_selecionada": return d.opcao;
    case "ajuda_aberta": case "ajuda_fechada": return [d.topico,d.camada].filter(Boolean).join(" · ");
    case "deslize_injetado": return d.proposta+" → TOCAR("+d.alvo+")";
    case "zoom_alterado": return number(d.anterior)+"× → "+number(d.novo)+"×";
    case "tarefa_encerrada": return d.resultado+(d.categorias?.length?" · "+d.categorias.join(", "):"");
    case "pedido_confirmado": return (d.pedido?.length??0)+" linhas no pedido";
    case "limite_atingido": return d.numero_acoes+" ações";
    default: return "";
  }
}
function renderMetrics(m){
  const ok=m.resultado==="sucesso";
  $("outcome").textContent=(m.resultado||"").replaceAll("_"," ");
  $("outcome").className="badge "+(ok?"done":"fail");
  $("tiles").replaceChildren(...tileSpec.map(([k,label,key])=>{
    const t=document.createElement("div");t.className="tile"+(key?" key":"");
    t.innerHTML='<div class="k"></div><div class="v"></div><div class="d"></div>';
    t.children[0].textContent=k;t.children[1].textContent=number(m[k]);t.children[2].textContent=label;
    return t;
  }));
  $("errors").replaceChildren(...Object.entries(m.erros||{}).map(([k,n])=>{
    const r=document.createElement("div");r.className="err"+(n?" hit":"");r.title=errorNames[k]||k;
    const b=document.createElement("b");b.textContent=k;const s=document.createElement("span");s.textContent=errorNames[k]||"";
    const c=document.createElement("span");c.className="n";c.textContent=n;r.append(b,s,c);return r;
  }));
  $("metrics").textContent=JSON.stringify(m,null,2);
}
function renderScenes(scene){
  visited.add(scene);
  $("scenes").replaceChildren(...Object.entries(sceneNames).map(([k,name])=>{
    const li=document.createElement("li");li.className=k===scene?"on":visited.has(k)?"seen":"";
    if(k===scene)li.setAttribute("aria-current","step");
    const b=document.createElement("b");b.textContent=k;li.append(b,name);return li;
  }));
}
function selectMode() {
  const mode=$("mode").value;
  $("mode-hint").textContent=modeHints[mode];
  $("zoom-label").hidden=mode!=="R";
  $("seed-label").hidden=mode==="manual";
  for(const option of $("task").options){
    option.disabled=mode!=="manual" && !["C1","C2"].includes(option.value);
  }
  if($("task").selectedOptions[0].disabled) $("task").value="C1";
}
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
  if(initial)visited=new Set();
  renderScenes(data.scene);
  $("mode-pill").textContent=modeNames[data.mode]+" · "+data.task+" · Versão "+data.version;
  $("version-info").textContent="Versão "+data.version+" · "+sceneNames[data.scene];
  $("task-info").textContent=data.task;
  $("instruction").textContent=data.instruction;
  $("quit").hidden=!manual || data.done;
  $("keys").hidden=data.mode==="R" || data.done;
  $("controls").hidden=manual;$("r-controls").hidden=data.mode!=="R";$("p-controls").hidden=data.mode!=="lens";
  $("lens-panel").hidden=manual;$("outline").hidden=manual;
  $("status").textContent="Passo "+data.step+(data.done?" · Encerrado":"");
  $("status").className="badge"+(data.done?" done":"");
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
    const px=Math.round, facts=[["Origem da região","x "+px(x)+" · y "+px(y)],["Recorte",px(largura)+" × "+px(altura)+" px"],
      ["Gestos disponíveis",String(data.public?.acoes?.length ?? 0)],["Memória",(data.public?.memoria?.length ?? 0)+" trechos"]];
    $("lens-facts").replaceChildren(...facts.map(([k,v])=>{
      const d=document.createElement("div"),dt=document.createElement("dt"),dd=document.createElement("dd");
      dt.textContent=k;dd.textContent=v;d.append(dt,dd);return d;
    }));
    drawLens();
  }
  renderEvents();
  $("results").hidden=!data.metrics;
  if(data.metrics)renderMetrics(data.metrics);
  if(data.done)stop();
}
function renderEvents(){
  $("trace").textContent=JSON.stringify(events.slice(-50),null,2);
  $("count").textContent=events.length+" eventos";
  const perception=new Set(["observacao","elemento_visto"]), shown=$("show-perception").checked?events:events.filter(e=>!perception.has(e.tipo));
  $("recent").replaceChildren(...shown.slice(-7).reverse().map(e=>{
    const li=document.createElement("li");
    const no=document.createElement("span");no.className="step-no";no.textContent=String(e.passo).padStart(2,"0");
    const tag=document.createElement("span");tag.className="ev "+eventKind(e.tipo);tag.textContent=e.tipo;
    const det=document.createElement("span");det.className="ev-detail";det.textContent=eventDetail(e);det.title=det.textContent;
    li.append(no,tag,det);return li;
  }));
}
async function start(){
  if(busy)return;
  stop();busy=true;$("error").textContent="";
  try {
    render(await request("/api/start",{task:$("task").value,mode:$("mode").value,version:$("version").value,
      zoom:Number($("zoom").value),seed:Number($("seed").value)}),true);
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
$("show-perception").onchange=renderEvents;
new ResizeObserver(drawLens).observe(lens);
start();
