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
``
    const body = {
        "location": {
            "row": row,
            "column": column,
        },
        "position": flapValues[position]
    }
    fetch(`/api/v1/modules/position`, {
        method: 'POST',
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(body)
    })
}

async function homeMove(row, column){
    console.log("Home button click");
    fetch(
        `/api/v1/modules/home?row=${row}&column=${column}`, {
            method: 'POST',
        }
    )
}

function createModuleCard(module){
        const container = document.querySelector(".module-container");
    if (!container) {
        console.warn('No .card-container element found to append app cards');
        return;
    }
    const card = document.createElement("div");
    card.className = "section-card section-card-module"
    
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
            const name = document.createElement("td");
            name.style.width = "60%";
            name.style.height = "22px";
            const data = document.createElement("td");
            data.style.width = "40%";
            name.innerHTML = key.toUpperCase();
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