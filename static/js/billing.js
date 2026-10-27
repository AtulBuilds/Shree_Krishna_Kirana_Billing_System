// Billing screen logic. The cart lives in this JavaScript array until you press "Save".
let cart = [];   // each item: {id, name, price, unit, stock, qty}

const $ = (id) => document.getElementById(id);
const scan = $("scan"), suggest = $("suggest"), msg = $("msg");

// Safely show text (prevents product names from being treated as HTML)
function esc(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}
const rupee = (n) => "₹" + n.toFixed(2);

function showMsg(text, isError) {
  msg.textContent = text;
  msg.className = "msg " + (isError ? "bad" : "good");
  setTimeout(() => { msg.textContent = ""; }, 3000);
}

function addToCart(p) {
  const found = cart.find((i) => i.id === p.id);
  if (found) {
    found.qty += 1;
  } else {
    cart.push({ id: p.id, name: p.name, price: p.price, unit: p.unit, stock: p.stock, qty: 1 });
  }
  const item = cart.find((i) => i.id === p.id);
  if (item.qty > item.stock) showMsg("Only " + item.stock + " in stock for " + item.name, true);
  render();
}

function render() {
  const tbody = document.querySelector("#cart tbody");
  tbody.innerHTML = "";
  let subtotal = 0, count = 0;
  cart.forEach((item, idx) => {
    const amount = item.price * item.qty;
    subtotal += amount;
    count += 1;
    const tr = document.createElement("tr");
    tr.innerHTML =
      "<td>" + (idx + 1) + "</td>" +
      "<td>" + esc(item.name) + " <small class='muted'>(" + esc(item.unit) + ")</small></td>" +
      "<td class='r'>" + rupee(item.price) + "</td>" +
      "<td><input class='qty' type='number' min='0.001' step='any' value='" + item.qty + "' data-idx='" + idx + "'></td>" +
      "<td class='r'>" + rupee(amount) + "</td>" +
      "<td><button class='btn small danger' data-del='" + idx + "'>✕</button></td>";
    tbody.appendChild(tr);
  });
  $("empty").style.display = cart.length ? "none" : "block";
  $("count").textContent = count;
  $("subtotal").textContent = rupee(subtotal);
  const discount = Math.min(Math.max(parseFloat($("discount").value) || 0, 0), subtotal);
  $("total").textContent = rupee(subtotal - discount);
}

// Change quantity / remove item
document.querySelector("#cart").addEventListener("input", (e) => {
  if (e.target.classList.contains("qty")) {
    const item = cart[+e.target.dataset.idx];
    item.qty = parseFloat(e.target.value) || 0;
    // update only totals (so the input does not lose focus while typing)
    let sub = 0;
    cart.forEach((i) => (sub += i.price * i.qty));
    $("subtotal").textContent = rupee(sub);
    const d = Math.min(Math.max(parseFloat($("discount").value) || 0, 0), sub);
    $("total").textContent = rupee(sub - d);
  }
});
document.querySelector("#cart").addEventListener("change", render);
document.querySelector("#cart").addEventListener("click", (e) => {
  if (e.target.dataset.del !== undefined) {
    cart.splice(+e.target.dataset.del, 1);
    render();
  }
});
$("discount").addEventListener("input", render);
$("clear").addEventListener("click", () => { cart = []; render(); scan.focus(); });

// Barcode scanner: it "types" the code very fast and presses Enter.
scan.addEventListener("keydown", async (e) => {
  if (e.key !== "Enter") return;
  e.preventDefault();
  const code = scan.value.trim();
  if (!code) return;
  const res = await fetch("/api/product?barcode=" + encodeURIComponent(code));
  if (res.ok) {
    addToCart(await res.json());
  } else {
    // not a barcode -> maybe a name search; add the first match
    const r2 = await fetch("/api/search?q=" + encodeURIComponent(code));
    const list = r2.ok ? await r2.json() : [];
    if (list.length) addToCart(list[0]);
    else showMsg("Product not found: " + code, true);
  }
  scan.value = "";
  suggest.innerHTML = "";
});

// Name search suggestions while typing
let timer;
scan.addEventListener("input", () => {
  clearTimeout(timer);
  const q = scan.value.trim();
  if (q.length < 2) { suggest.innerHTML = ""; return; }
  timer = setTimeout(async () => {
    const res = await fetch("/api/search?q=" + encodeURIComponent(q));
    if (!res.ok) return;
    const list = await res.json();
    suggest.innerHTML = "";
    list.forEach((p) => {
      const b = document.createElement("button");
      b.type = "button";
      b.innerHTML = esc(p.name) + " <small>" + rupee(p.price) + " · stock " + p.stock + "</small>";
      b.onclick = () => { addToCart(p); scan.value = ""; suggest.innerHTML = ""; scan.focus(); };
      suggest.appendChild(b);
    });
  }, 250);
});

// Save the bill
async function checkout() {
  if (!cart.length) return showMsg("Cart is empty.", true);
  if (cart.some((i) => !(i.qty > 0))) return showMsg("Fix quantities first.", true);
  $("checkout").disabled = true;
  try {
    const res = await fetch("/api/checkout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        items: cart.map((i) => ({ id: i.id, qty: i.qty })),
        discount: parseFloat($("discount").value) || 0,
        customer_name: $("customer").value,
        payment_method: $("payment").value,
      }),
    });
    const data = await res.json();
    if (res.ok) {
      window.location = data.url;   // open the printable invoice
    } else {
      showMsg(data.error || "Could not save bill.", true);
    }
  } catch (err) {
    showMsg("Network problem. Is the server running?", true);
  }
  $("checkout").disabled = false;
}
$("checkout").addEventListener("click", checkout);

// Keyboard shortcuts
document.addEventListener("keydown", (e) => {
  if (e.key === "F2") { e.preventDefault(); scan.focus(); }
  if (e.key === "F9") { e.preventDefault(); checkout(); }
});

render();
