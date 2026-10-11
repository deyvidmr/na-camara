// Na Câmara: jornada tema -> projetos -> "como você votaria?" -> como a Câmara votou.
// Rotas pelo fragmento da URL: #/ , #/tema/<slug> , #/projeto/<id>?tema=<slug>
"use strict";

const app = document.getElementById("app");

async function api(caminho) {
  const r = await fetch("/api" + caminho);
  if (!r.ok) throw new Error(r.status === 404 ? "Não encontramos esta página." : "Não foi possível carregar os dados agora.");
  return r.json();
}

function esc(texto) {
  return String(texto ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function data(iso) {
  if (!iso) return "";
  const [a, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${a}`;
}

function barra(sim, nao, outros, grande = false) {
  return `<div class="barra${grande ? " grande" : ""}" role="img" aria-label="${sim} votos Sim, ${nao} Não, ${outros} outros">
    <i class="sim" style="flex:${sim}"></i><i class="nao" style="flex:${nao}"></i><i class="outro" style="flex:${outros}"></i></div>`;
}

const NOME_VOTO = { sim: "Sim", nao: "Não", abstencao: "Abstenção", obstrucao: "Obstrução", presidente: "Presidindo", secreto: "Secreto", liberado: "Liberado" };
const CLASSE_VOTO = { sim: "sim", nao: "nao" };
function chipVoto(v) {
  return `<span class="voto ${CLASSE_VOTO[v] || "outro"}">${esc(NOME_VOTO[v] || v || "sem orientação")}</span>`;
}

// A resposta do usuário fica só neste navegador (localStorage), nunca vai ao servidor.
const memoria = {
  ler(chave) { try { return localStorage.getItem(chave); } catch { return null; } },
  gravar(chave, valor) { try { localStorage.setItem(chave, valor); } catch { /* navegador sem armazenamento */ } },
};

let temasCache = null;
async function temas() {
  temasCache ??= await api("/temas");
  return temasCache;
}

// ---------- início ----------
async function telaInicio() {
  const lista = await temas();
  document.title = "Na Câmara";
  app.innerHTML = `
    <section>
      <h1>O que mais pesa na sua vida?</h1>
      <p class="lede">Escolha um tema. Mostramos o que a Câmara dos Deputados votou sobre ele, você diz como votaria e compara com o voto de cada partido. Não precisa entender de política.</p>
    </section>
    <nav class="temas" aria-label="Temas">
      ${lista.map((t) => `
        <a class="tema" href="#/tema/${esc(t.tema_slug)}">
          <b>${esc(t.nome)}</b>
          <span class="muted pequeno">${esc(t.descricao)}</span>
          <span class="qtd">${t.projetos} ${t.projetos === 1 ? "projeto votado" : "projetos votados"}</span>
        </a>`).join("")}
    </nav>`;
}

// ---------- tema ----------
const ORDENS = { relevancia: "Mais ligados ao tema", recentes: "Mais recentes", divididos: "Mais divididos" };

async function telaTema(slug, ordem = "relevancia") {
  const tema = (await temas()).find((t) => t.tema_slug === slug);
  if (!tema) throw new Error("Não encontramos este tema.");
  const projetos = await api(`/temas/${encodeURIComponent(slug)}/projetos?ordem=${ordem}`);
  document.title = `${tema.nome} · Na Câmara`;
  app.innerHTML = `
    <a class="voltar" href="#/">← Todos os temas</a>
    <section>
      <h1>${esc(tema.nome)}</h1>
      <p class="lede">${esc(tema.descricao)}. Projetos que tiveram votação nominal no Plenário da Câmara, em que cada deputado registrou seu voto.</p>
      <div class="abas" role="group" aria-label="Ordenar projetos">
        ${Object.entries(ORDENS).map(([k, rot]) => `<button type="button" data-ordem="${k}" aria-pressed="${k === ordem}">${rot}</button>`).join("")}
      </div>
    </section>
    <div class="projetos">
      ${projetos.map((p) => `
        <a class="projeto" href="#/projeto/${p.proposicao_id}?tema=${esc(slug)}">
          <div class="projeto-topo">
            <span class="mono">${esc(p.projeto)}</span>
            ${p.grau === 3 ? '<span class="chip">Afeta diretamente</span>' : ""}
          </div>
          <p>${esc(p.justificativa)}</p>
          ${barra(p.placar.sim, p.placar.nao, p.placar.outros)}
          <span class="muted pequeno">${p.aprovada === false ? "Rejeitado" : "Aprovado"} na Câmara em ${data(p.data_votacao)}: <span class="mono">${p.placar.sim} Sim × ${p.placar.nao} Não</span></span>
        </a>`).join("") || '<p class="muted">Nenhum projeto votado neste tema ainda.</p>'}
    </div>
    <p class="muted pequeno">O texto de cada projeto é um resumo feito por IA a partir da ementa oficial, revisável por pessoas. Abra o projeto para ver a ementa e as fontes.</p>`;
  app.querySelectorAll("[data-ordem]").forEach((b) => b.addEventListener("click", () => telaTema(slug, b.dataset.ordem).catch(mostrarErro)));
}

// ---------- projeto ----------
function semPlacar(descricao) {
  // "Aprovado o Projeto... Sim: 325; não: 97; total: 423." -> "Aprovado o Projeto..."
  return descricao.replace(/\s*Sim\s*:.*$/is, "").trim();
}

const NOME_TIPO = { texto_principal: "Texto principal", texto_senado: "Mudanças feitas pelo Senado" };

async function telaProjeto(id, temaSlug) {
  const p = await api(`/projetos/${encodeURIComponent(id)}`);
  const vp = p.votacao_principal;
  const v = vp ? await api(`/votacoes/${encodeURIComponent(vp.votacao_id)}?incluir_votos=true`) : null;
  const temaAtual = p.temas.find((t) => t.tema_slug === temaSlug) || p.temas[0];
  const autores = p.autores.slice(0, 3).map((a) => a.nome + (a.partido ? ` (${a.partido}${a.uf ? "-" + a.uf : ""})` : "")).join(", ")
    + (p.autores.length > 3 ? ` e mais ${p.autores.length - 3}` : "");
  document.title = `${p.nome} · Na Câmara`;

  app.innerHTML = `
    <a class="voltar" href="${temaSlug ? `#/tema/${esc(temaSlug)}` : "#/"}">← Voltar</a>
    <section>
      <div class="abas">${p.temas.map((t) => `<span class="chip">${esc(t.tema)}</span>`).join("")}</div>
      <h1>${esc(p.nome)}</h1>
      ${temaAtual ? `<p class="lede">${esc(temaAtual.justificativa)}</p>` : ""}
      <div class="fatos">
        <div><span class="label">Situação</span><b>${esc(p.situacao || "não informada")}</b></div>
        ${autores ? `<div><span class="label">Autoria</span><span>${esc(autores)}</span></div>` : ""}
        ${vp ? `<div><span class="label">Votação na Câmara</span><b class="mono">${data(vp.data)}</b></div>` : ""}
      </div>
      <div class="ementa"><span class="label">Ementa oficial</span><p>${esc(p.ementa)}</p></div>
    </section>
    ${v ? secaoVoto(v) : '<p class="muted">Este projeto ainda não teve votação nominal do texto no Plenário.</p>'}
    ${p.outras_votacoes.length ? `
      <section>
        <h2>Outras votações deste texto</h2>
        <p class="muted pequeno">Propostas de emenda à Constituição são votadas em dois turnos, e projetos que voltam do Senado têm as mudanças votadas de novo.</p>
        <ul class="votacoes">
          ${p.outras_votacoes.map((o) => `
            <li>
              <span class="label">${esc(NOME_TIPO[o.tipo] || o.tipo)} · ${data(o.data)}</span>
              <span>${esc(semPlacar(o.descricao))}</span>
              ${barra(o.placar.sim, o.placar.nao, o.placar.outros)}
              <span class="mono pequeno">${o.placar.sim} Sim × ${o.placar.nao} Não</span>
            </li>`).join("")}
        </ul>
      </section>` : ""}
    <section>
      <h2>Fontes</h2>
      <ol class="fontes">
        <li><a href="https://www.camara.leg.br/propostas-legislativas/${p.proposicao_id}">Ficha do ${esc(p.nome)} na Câmara</a></li>
        ${p.url_inteiro_teor ? `<li><a href="${esc(p.url_inteiro_teor)}">Texto original do projeto</a></li>` : ""}
        ${vp ? `<li><a href="https://dadosabertos.camara.leg.br/api/v2/votacoes/${esc(vp.votacao_id)}/votos">Votos registrados (Dados Abertos da Câmara)</a></li>` : ""}
      </ol>
    </section>`;

  if (v) ligarVoto(v);
}

function secaoVoto(v) {
  return `
    <section>
      <h2>E você, como votaria?</h2>
      <div class="pergunta">
        <p>Em ${data(v.data)}, os deputados votaram isto:</p>
        <p><b>${esc(semPlacar(v.descricao))}</b></p>
        <div class="opcoes" role="group" aria-label="Seu voto">
          <button type="button" data-voto="sim">Sim</button>
          <button type="button" data-voto="nao">Não</button>
          <button type="button" data-voto="abstencao">Me absteria</button>
          <button type="button" data-voto="nao_sei">Ainda não sei</button>
        </div>
        <button type="button" class="pular" data-voto="pular">Pular e ver o resultado</button>
        <p class="muted pequeno">Sua resposta fica só neste navegador.</p>
      </div>
    </section>
    <section id="resultado" hidden>
      <h2>Como a Câmara votou</h2>
      <p class="resposta" id="resposta"></p>
      ${barra(v.placar.sim, v.placar.nao, v.placar.outros, true)}
      <div class="legenda">
        <span><i class="sim"></i>Sim <b class="mono">${v.placar.sim}</b></span>
        <span><i class="nao"></i>Não <b class="mono">${v.placar.nao}</b></span>
        <span><i class="outro"></i>Outros <b class="mono">${v.placar.outros}</b></span>
      </div>
      ${v.liderancas.length ? `
        <h3>O que pediram as lideranças</h3>
        <div class="liderancas">${v.liderancas.map((l) => `<span class="lideranca">${esc(l.bancada)}: ${chipVoto(l.orientacao)}</span>`).join("")}</div>` : ""}
      <h3>Por partido</h3>
      <div class="tabela">
        <table>
          <thead><tr><th>Partido</th><th>Orientação</th><th>Votos</th><th class="num">Sim</th><th class="num">Não</th></tr></thead>
          <tbody id="partidos"></tbody>
        </table>
      </div>
      <p class="muted pequeno">Orientação é o que a liderança pediu à bancada. Quando o partido estava num bloco ou federação, vale a orientação do grupo; * indica bloco cuja composição deduzimos dos dados, porque a Câmara não publica a lista completa.</p>
      <h3>Deputado por deputado</h3>
      <label class="pequeno" for="busca">Procure por nome, partido ou estado</label>
      <input id="busca" class="busca" type="search" placeholder="Ex.: SP, PT, Maria">
      <div class="deputados"><table><tbody id="deputados"></tbody></table></div>
      <p class="nota">"Sim" responde à pergunta desta votação. Quem faltou à sessão não aparece, e ausência não conta como voto contra.</p>
    </section>`;
}

function ligarVoto(v) {
  const chave = `voto:${v.votacao_id}`;
  const resultado = document.getElementById("resultado");
  const botoes = app.querySelectorAll(".opcoes [data-voto]");

  function mostrar(escolha) {
    botoes.forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.voto === escolha)));
    const mesmos = { sim: v.placar.sim, nao: v.placar.nao }[escolha];
    document.getElementById("resposta").innerHTML = escolha === "sim" || escolha === "nao"
      ? `Você votaria <b>${NOME_VOTO[escolha]}</b>, como ${mesmos} deputados. Os partidos marcados na tabela tiveram maioria igual à sua.`
      : escolha === "abstencao" ? "Você se absteria. Veja abaixo como cada partido votou."
      : "Tudo bem não ter uma opinião. Veja abaixo como cada partido votou.";
    tabelaPartidos(v, escolha);
    resultado.hidden = false;
  }

  app.querySelectorAll("[data-voto]").forEach((b) => b.addEventListener("click", () => {
    const escolha = b.dataset.voto;
    const primeiraVez = resultado.hidden;
    if (escolha !== "pular") memoria.gravar(chave, escolha);
    mostrar(escolha);
    if (primeiraVez) {
      resultado.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
    }
  }));

  const anterior = memoria.ler(chave);
  if (anterior) mostrar(anterior);

  const busca = document.getElementById("busca");
  busca.addEventListener("input", () => tabelaDeputados(v, busca.value));
  tabelaDeputados(v, "");
}

function tabelaPartidos(v, escolha) {
  document.getElementById("partidos").innerHTML = v.partidos.map((p) => {
    const maioria = p.sim > p.nao ? "sim" : p.nao > p.sim ? "nao" : null;
    const inferido = p.orientacao_origem === "inferido" ? "*" : "";
    return `<tr class="${maioria && maioria === escolha ? "igual" : ""}">
      <td><b>${esc(p.partido)}</b></td>
      <td>${p.orientacao ? chipVoto(p.orientacao) : '<span class="ori">sem orientação</span>'}<span class="ori">${inferido}</span></td>
      <td class="mini">${barra(p.sim, p.nao, p.outros)}</td>
      <td class="num">${p.sim}</td><td class="num">${p.nao}</td></tr>`;
  }).join("");
}

function tabelaDeputados(v, filtro) {
  const f = filtro.trim().toLowerCase();
  const lista = (v.votos || []).filter((d) => !f || `${d.nome} ${d.partido} ${d.uf}`.toLowerCase().includes(f));
  document.getElementById("deputados").innerHTML = lista.map((d) => `
    <tr><td>${esc(d.nome)}</td><td class="ori">${esc(d.partido || "")}-${esc(d.uf || "")}</td><td>${chipVoto(d.voto)}</td></tr>`).join("")
    || '<tr><td class="muted">Ninguém encontrado.</td></tr>';
}

// ---------- roteamento ----------
function mostrarErro(e) {
  app.innerHTML = `<p class="erro">${esc(e.message)} <a href="#/">Voltar ao início</a></p>`;
}

async function rotear() {
  const [caminho, consulta] = location.hash.replace(/^#/, "").split("?");
  const partes = caminho.split("/").filter(Boolean);
  const params = new URLSearchParams(consulta || "");
  app.innerHTML = '<p class="carregando">Carregando…</p>';
  try {
    if (partes[0] === "tema" && partes[1]) await telaTema(partes[1]);
    else if (partes[0] === "projeto" && partes[1]) await telaProjeto(partes[1], params.get("tema"));
    else await telaInicio();
    window.scrollTo(0, 0);
  } catch (e) {
    mostrarErro(e);
  }
}

window.addEventListener("hashchange", rotear);
rotear();
