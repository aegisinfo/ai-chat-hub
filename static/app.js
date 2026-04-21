async function safeFetch(url, options = {}) {
    const res = await fetch(url, options);

    if (!res.ok) {
        const text = await res.text();
        console.error("SERVER ERROR:", text);
        return null;
    }

    return res.json();
}

// SEND
async function send() {
    const input = document.getElementById("input");
    const text = input.value;
    input.value = "";

    const data = await safeFetch("/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({prompt: text})
    });

    if (!data) return;

    document.getElementById("claude").innerText = data.claude;
    document.getElementById("groq").innerText = data.groq;

    loadRecent();
}

// LOAD RECENT
async function loadRecent() {
    const data = await safeFetch("/recent");
    if (!data) return;

    const h = document.getElementById("history");
    h.innerHTML = "";

    data.forEach(c => {
        const b = document.createElement("button");
        b.innerText = c.title;
        b.onclick = () => loadConversation(c.id);
        h.appendChild(b);
    });
}

// LOAD CONVO
async function loadConversation(id) {
    const data = await safeFetch("/conversation/" + id);
    if (!data) return;

    let claude = "", groq = "";

    data.forEach(m => {
        if (m[0] === "claude") claude = m[1];
        if (m[0] === "groq") groq = m[1];
    });

    document.getElementById("claude").innerText = claude;
    document.getElementById("groq").innerText = groq;
}

// SEARCH
async function searchChats() {
    const q = document.getElementById("searchBox").value;

    const data = await safeFetch("/search?q=" + encodeURIComponent(q));
    if (!data) return;

    const h = document.getElementById("history");
    h.innerHTML = "";

    data.forEach(c => {
        const b = document.createElement("button");
        b.innerText = "Result " + c.id;
        b.onclick = () => loadConversation(c.id);
        h.appendChild(b);
    });
}

// INIT
document.addEventListener("DOMContentLoaded", loadRecent);
