"use strict";
const phone = document.getElementById("phone");
const surface = document.getElementById("surface");
const footer = document.getElementById("footer");
const error = document.getElementById("demo-error");
let current, busy = false;

function renderSign(sign) {
  const element = document.createElement(sign.action ? "button" : "div");
  const [x, y, width, height] = sign.box;
  element.className = "sign " + sign.style + (sign.action ? " tap" : "");
  element.dataset.sign = sign.id;
  element.style.left = (100 * x / 360) + "%";
  element.style.width = (100 * width / 360) + "%";
  element.style.top = (sign.fixed ? y - 800 : y) + "px";
  element.style.height = height + "px";
  const lines = document.createElement("span");
  lines.className = "lines";
  for (const line of sign.text_lines) {
    const row = document.createElement("span");
    row.className = "line";
    row.textContent = line.text;
    lines.append(row);
  }
  element.append(lines);
  if (sign.action) {
    element.type = "button";
    element.onclick = () => act(sign.action);
    if (sign.selected !== undefined) element.setAttribute("aria-pressed", String(sign.selected));
    if (sign.part && sign.part !== "name" && sign.action.startsWith("open:")) element.tabIndex = -1;
    if (sign.text === "+" || sign.text === "−") {
      const name = current.elements.find(s => s.id === "line:" + sign.line)?.text;
      element.setAttribute("aria-label", (sign.text === "+" ? "Aumentar" : "Diminuir") +
        " quantidade" + (name ? " de " + name : ""));
    }
  } else if (sign.role === "heading" || sign.role === "name") {
    element.setAttribute("role", "heading");
    element.setAttribute("aria-level", "2");
  }
  return element;
}

function render(data, reset) {
  const sceneChanged = reset || current?.scene !== data.scene;
  const focused = document.activeElement?.dataset.sign;
  const scroll = phone.scrollTop;
  current = data;
  surface.replaceChildren();
  footer.replaceChildren();
  for (const sign of data.elements) (sign.fixed ? footer : surface).append(renderSign(sign));
  let height = data.height;
  if (data.photo) {
    const top = Math.max(...data.elements.map(sign => sign.box[1] + sign.box[3])) + 20;
    height = Math.max(height, top + 198);
    const figure = document.createElement("figure");
    figure.className = "dish-preview";
    figure.style.top = top + "px";
    const image = document.createElement("img");
    image.src = data.photo;
    image.alt = "";
    image.width = 328;
    image.height = 156;
    image.decoding = "async";
    const caption = document.createElement("figcaption");
    caption.textContent = "Imagem ilustrativa";
    figure.append(image, caption);
    image.onerror = () => { figure.hidden = true; surface.style.height = data.height + "px"; };
    surface.append(figure);
  }
  surface.style.height = height + "px";
  phone.scrollTop = sceneChanged ? 0 : scroll;
  if (sceneChanged && !reset) phone.focus({preventScroll:true});
  else if (focused) {
    [...surface.children, ...footer.children].find(node => node.dataset.sign === focused)
      ?.focus({preventScroll:true});
  }
}

async function request(route, body, reset = false) {
  if (busy) return;
  busy = true;
  error.textContent = "";
  try {
    const response = await fetch(route, {
      method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    render(data, reset);
  } catch (failure) {
    error.textContent = failure.message || "Não foi possível atualizar a demonstração.";
  } finally {
    busy = false;
  }
}

const start = () => request("/api/start", {version:document.getElementById("demo-version").value}, true);
const act = action => request("/api/action", {session:current.session, action});
document.getElementById("demo-settings").onsubmit = event => { event.preventDefault(); start(); };
document.addEventListener("keydown", event => {
  const action = event.key === "F1" ? "help" : event.key === "Escape" ? "back" : null;
  if (action && current?.elements.some(sign => sign.action === action)) {
    event.preventDefault();
    act(action);
  }
});
start();
