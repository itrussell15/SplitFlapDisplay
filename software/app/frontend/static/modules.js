import {getFlaps} from './common.js';

let flapValues = null;

async function init()
{

    flapValues = await getFlaps();
    console.log(flapValues);
    console.log("Module Page loaded");
    await updateModules();
}

async function updateModules() {
    const request = await fetch("/api/v1/display/modules");
    let modules = await request.json();
    modules.locations.forEach(module => createModuleCard(module));
}

async function positionMove(row, column, position){

    const body = {
        "location": {
            "row": row,
            "column": column,
        },
        "position": flapValues[position]
    }
    const response = await fetch(`/api/v1/modules/position`, {
        method: 'POST',
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(body)
    });

    if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
    }
    const data = await response.json();
    updateModuleInfo(row, column, "steps", data.data_value);
}

async function homeMove(row, column){
    console.log("Home button click");
    const request_data = fetch(
        `/api/v1/modules/home?row=${row}&column=${column}`, {
            method: 'POST',
        }
    );
    updateModuleInfo(row, column, "steps", 0);
}

async function updateModuleInfo(row, column, key, value)
{
    const selector = `.module-container .section-card[data-location="${row}x${column}"]`;
    const card = document.querySelector(selector);

    const tableRow = card.querySelector(`tr[data-key="${key}"]`);
    const valueCell = tableRow.querySelector('td[data-role="value"]');
    if (!valueCell) return;
    valueCell.textContent = value;
}

function createModuleCard(module){
        const container = document.querySelector(".module-container");
    if (!container) {
        console.warn('No .card-container element found to append app cards');
        return;
    }
    const card = document.createElement("div");
    card.className = "section-card section-card-module"
    card.dataset.location = `${module.location.row}x${module.location.column}`;
    
    const header = document.createElement("div");
    header.className = "module-card module-card-header";
    header.innerHTML = `
        <h4 class="section-title">${module.location.row} , ${module.location.column}</h4>
    `;

    const body = document.createElement("div");
    body.className = "module-card-body";
    const table = document.createElement("div");
    
    Object.entries(module.info).forEach(
        ([key, value]) => {
            const row = document.createElement("tr");
            row.dataset["key"] = key;
            const name = document.createElement("td");
            name.style.width = "60%";
            name.style.height = "22px";
            name.dataset.role = "key";
            name.innerHTML = key.toUpperCase();
            
            const data = document.createElement("td");
            data.dataset.role = "value";
            data.innerHTML = value;

            row.append(name);
            row.append(data);
            table.append(row);
        }
    )
    body.append(table);

    const footer = document.createElement("div");
    footer.className = "module-card-footer";

    const homeButton = document.createElement("button");
    homeButton.className = "btn btn-module";
    homeButton.innerHTML = `HOME`;
    homeButton.addEventListener("click", () => homeMove(module.location.row, module.location.column));
    footer.appendChild(homeButton);

    const flapSelector = document.createElement("select");
    flapSelector.className = "flap-selector";
    Object.keys(flapValues).forEach(flap => {
        const opt = document.createElement('option');
        opt.value = flap;
        opt.textContent = flap;
        flapSelector.appendChild(opt);
    });

    const moveButton = document.createElement("button");
    moveButton.className = "btn btn-module";
    moveButton.innerHTML = `MOVE`;
    moveButton.addEventListener("click", () => positionMove(module.location.row, module.location.column, flapSelector.value));
    
    footer.appendChild(moveButton);
    footer.appendChild(flapSelector);

    card.appendChild(header);
    card.appendChild(body);
    card.appendChild(footer);
    container.appendChild(card);
}

// Called on Startup
document.addEventListener("DOMContentLoaded", init);