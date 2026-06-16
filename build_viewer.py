import json
import sys
from pathlib import Path


def load_json(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data

    return [data]


def slim(rows):
    out = []

    for row in rows:
        r = dict(row)

        # remover campos gigantes
        r.pop("full_text", None)
        r.pop("pages", None)

        out.append(r)

    return out


def build(json_path):
    rows = slim(load_json(json_path))

    payload = json.dumps(
        rows,
        ensure_ascii=False,
        separators=(",", ":")
    )

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TCE-AL Viewer</title>

<style>
*,*::before,*::after{{
    box-sizing:border-box;
    margin:0;
    padding:0;
}}

body{{
    font-family:system-ui,-apple-system,sans-serif;
    font-size:14px;
    background:#f5f4f1;
    color:#1a1a18;
    min-height:100vh;
}}

#topbar{{
    background:#fff;
    border-bottom:1px solid #e0ddd6;
    padding:14px 24px;
    display:flex;
    align-items:center;
    gap:16px;
    position:sticky;
    top:0;
    z-index:10;
}}

#topbar h1{{
    font-size:15px;
    font-weight:600;
}}

#sid-sel{{
    min-width:350px;
    max-width:600px;
    font-size:13px;
    padding:6px 10px;
    border:1px solid #d0cdc6;
    border-radius:6px;
    background:#fff;
    cursor:pointer;
}}

.count-badge{{
    font-size:12px;
    color:#888780;
    margin-left:auto;
}}

#main{{
    max-width:1200px;
    margin:0 auto;
    padding:24px;
}}

#meta-grid{{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
    gap:10px;
    margin-bottom:28px;
}}

.meta-card{{
    background:#fff;
    border:1px solid #e8e5de;
    border-radius:10px;
    padding:12px 16px;
}}

.meta-card .lbl{{
    font-size:10px;
    text-transform:uppercase;
    letter-spacing:.06em;
    color:#888780;
    margin-bottom:5px;
}}

.meta-card .val{{
    font-size:13px;
    font-weight:500;
    word-break:break-all;
}}

.badge{{
    display:inline-block;
    font-size:10px;
    padding:2px 8px;
    border-radius:999px;
}}

.badge-ok{{
    background:#EAF3DE;
    color:#3B6D11;
}}

.badge-no{{
    background:#FCEBEB;
    color:#A32D2D;
}}

#indice-section,
#atos-section{{
    background:#fff;
    border:1px solid #e8e5de;
    border-radius:10px;
    padding:16px 20px;
    margin-bottom:28px;
}}

.section-title{{
    font-size:12px;
    text-transform:uppercase;
    letter-spacing:.06em;
    color:#888780;
    margin-bottom:12px;
}}

.indice-list{{
    list-style:none;
}}

.sec-row{{
    padding:6px 8px;
    margin:8px 0 4px;
    background:#f5f4f1;
    border-radius:6px;
    font-size:12px;
    font-weight:600;
}}

.act-row{{
    display:flex;
    gap:10px;
    padding:4px 8px;
    border-bottom:1px solid #f0ede6;
}}

.act-pg{{
    min-width:40px;
    color:#888780;
}}

.act-name{{
    flex:1;
}}

.ato-block{{
    display:grid;
    grid-template-columns:220px 1fr;
    border:1px solid #e8e5de;
    border-radius:10px;
    overflow:hidden;
    margin-bottom:14px;
}}

.ato-left{{
    background:#f5f4f1;
    border-right:1px solid #e8e5de;
    padding:16px;
}}

.ato-right{{
    padding:16px;
}}

.ato-index{{
    font-size:11px;
    color:#999;
    margin-bottom:10px;
}}

.ato-path{{
    display:flex;
    flex-direction:column;
    gap:6px;
}}

.ato-crumb{{
    font-size:12px;
}}

.ato-text{{
    white-space:pre-wrap;
    line-height:1.7;
}}

.page-break-marker{{
    margin:12px 0;
    border:none;
    border-top:1px dashed #ccc;
}}

@media(max-width:640px){{
    .ato-block{{
        grid-template-columns:1fr;
    }}

    .ato-left{{
        border-right:none;
        border-bottom:1px solid #e8e5de;
    }}
}}
</style>
</head>

<body>

<div id="topbar">
    <h1>TCE-AL</h1>

    <select id="sid-sel"></select>

    <span class="count-badge" id="ato-count"></span>
</div>

<div id="main">

    <div id="meta-grid"></div>

    <div id="indice-section" style="display:none">
        <div class="section-title">Índice</div>
        <ul class="indice-list" id="indice-list"></ul>
    </div>

    <div id="atos-section" style="display:none">
        <div class="section-title">Atos</div>
        <div id="atos-list"></div>
    </div>

</div>

<script>

const DATA = {payload};

console.log("TOTAL:", DATA.length);
console.log("SOURCE IDS:", DATA.map(x => x.source_id));

function esc(s){{
    return String(s ?? '')
        .replace(/&/g,'&amp;')
        .replace(/</g,'&lt;')
        .replace(/>/g,'&gt;');
}}

function tryParse(v){{
    if(v == null) return null;

    if(typeof v === 'object')
        return v;

    try {{
        return JSON.parse(v);
    }}
    catch(e) {{
        return v;
    }}
}}

function renderMeta(row){{
    const fields = [
        ['source_id', row.source_id],
        ['edition_number', row.edition_number],
        ['header_date_raw', row.header_date_raw],
        ['total_pages', row.total_pages],
        ['has_indice', row.has_indice],
        ['pdf_path', row.pdf_path]
    ];

    document.getElementById('meta-grid').innerHTML =
        fields.map(([k,v])=>{{

            let value='';

            if(k==='has_indice'){{
                value = v
                    ? '<span class="badge badge-ok">sim</span>'
                    : '<span class="badge badge-no">não</span>';
            }}
            else {{
                value = esc(v ?? '—');
            }}

            return `
            <div class="meta-card">
                <div class="lbl">${{esc(k)}}</div>
                <div class="val">${{value}}</div>
            </div>`;
        }}).join('');
}}

function renderIndice(row){{
    const sec = document.getElementById('indice-section');
    const list = document.getElementById('indice-list');

    const indice = tryParse(row.indice);

    if(!indice || !indice.length){{
        sec.style.display='none';
        return;
    }}

    sec.style.display='block';

    list.innerHTML = indice.map(x => {{
        if(x.type === 'section')
            return `<li class="sec-row">${{esc(x.title || '')}}</li>`;

        return `
        <li class="act-row">
            <span class="act-pg">p.${{esc(x.page)}}</span>
            <span class="act-name">${{esc(x.act || '')}}</span>
        </li>`;
    }}).join('');
}}

function renderAtos(row){{
    const atos = tryParse(row.atos);

    const sec = document.getElementById('atos-section');
    const list = document.getElementById('atos-list');

    if(!atos || !atos.length){{
        sec.style.display='none';
        document.getElementById('ato-count').textContent='';
        return;
    }}

    sec.style.display='block';

    document.getElementById('ato-count').textContent =
        `${{atos.length}} ato(s)`;

    list.innerHTML='';

    atos.forEach((ato, idx) => {{

        const path = String(ato[0] || '');
        const text = String(ato[1] || '');

        const crumbs = path
            .split(';')
            .map(x => x.trim())
            .filter(Boolean);

        const div = document.createElement('div');

        div.className='ato-block';

        div.innerHTML = `
            <div class="ato-left">
                <div class="ato-index">ato ${{idx+1}}</div>

                <div class="ato-path">
                    ${{crumbs.map(c =>
                        `<div class="ato-crumb">${{esc(c)}}</div>`
                    ).join('')}}
                </div>
            </div>

            <div class="ato-right">
                <div class="ato-text">
                    ${{
                        text
                        .split(/\\n---\\s*PAGE BREAK\\s*---\\n/i)
                        .map(x => esc(x))
                        .join('<hr class="page-break-marker">')
                    }}
                </div>
            </div>
        `;

        list.appendChild(div);
    }});
}}

function renderRow(row){{
    renderMeta(row);
    renderIndice(row);
    renderAtos(row);
}}

const sel = document.getElementById('sid-sel');

DATA.forEach((row, idx) => {{

    const opt = document.createElement('option');

    opt.value = idx;

    opt.textContent =
        `source_id=${{row.source_id}} | edição=${{row.edition_number}}`;

    sel.appendChild(opt);
}});

sel.addEventListener('change', e => {{

    const idx = Number(e.target.value);

    console.log('selected idx', idx);

    if(
        Number.isFinite(idx) &&
        idx >= 0 &&
        idx < DATA.length
    ){{
        renderRow(DATA[idx]);
    }}
}});

if(DATA.length > 0){{
    sel.value = "0";
    renderRow(DATA[0]);
}}

</script>
</body>
</html>
"""

    output = Path("viewer.html")

    output.write_text(
        html,
        encoding="utf-8"
    )

    print(f"Viewer salvo em: {output.resolve()}")
    print(f"Registros carregados: {len(rows):,}")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "tce_sample.json"
    build(path)