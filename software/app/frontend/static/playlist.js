
let apps = [];
let defaultApp = null;
let selectedIndex = 0;

async function init()
{   
    await createSelectItems();
    defaultApp = apps[0];
    console.log(`Default App: ${defaultApp.name}`);
    await updatePlaylistContainer();

    const createItemButton = document.getElementById('popup-create-item');
    const popup = document.getElementById('playlist-popup');

    if (!popup) return;

    createItemButton?.addEventListener("click", async (event) => {
        const isItemCreated = createItem();
        if (isItemCreated) {
            popup.classList.remove("open");
            popup.setAttribute("aria-hidden", "true");
        }
        else {
            console.warn("Unable to close due to invalid form entry");
        }
    });

    const appSelector = document.getElementById("app-selector");
    appSelector.addEventListener('change', (event) => {
        const selectedValue = event.target;
        const selectedOptions = selectedValue.selectedOptions;
        selectedIndex = selectedOptions[0].dataset.index;
        loadAppParams(selectedIndex);
    });
}

async function createSelectItems(){
    const appsRequest = await fetch("/api/v1/apps/list");
    console.log(`App Options: ${appsRequest}`)
    const data = await appsRequest.json();
    apps = data.apps ?? [];
    if (!apps){
        console.error("Error fetching the available apps");
        return;
    }

    const container = document.querySelector('.selection');
    const selector = document.createElement("select");
    selector.id = "app-selector";
    apps.forEach((app, index) => {
        const option = document.createElement("option");
        option.textContent = app.name;
        option.dataset.index = index;
        selector.appendChild(option);
    });
    container.appendChild(selector);
    console.log("Selector created");
    loadAppParams(0);
}

async function createItem() {
    console.log("Creating Item");
    let validEntry = true;
    const entries = {};
    const itemSelect = document.querySelector("#app-selector");
    const forms = document.querySelectorAll(".parameter-row");
    forms.forEach(form => {
        console.log(form);
        const entryValue = form.querySelector(".parameter-form").value;
        if (!entryValue || entryValue === ""){
            console.error(`${form.dataset.key} entry is not valid`);
            validEntry = false;
            form.className = "parameter-row parameter-row-fail";
        }
        else{
            form.className = "parameter-row";
        }
        entries[form.dataset.key] = form.querySelector(".parameter-form").value;
    })

    if (validEntry){
        console.log("Submission is valid");
        console.log(entries);
        const body = {"item_type": itemSelect.value, "parameters": entries};
        const response = await fetch(`/api/v1/playlist/add`, {
            method: 'POST',
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(body)
        });
        await updatePlaylistContainer();
    }
    
    return validEntry;
}

async function updatePlaylistContainer() {
    const playlistRequest = await fetch("/api/v1/playlist/list");
    if (!playlistRequest.ok) {
        throw new Error(`Request failed: ${playlistRequest.status}`);
    }
    const playlistItems = await playlistRequest.json();

    const playlistContainer = document.querySelector(".playlist-container");
    if (!playlistContainer){
        console.error("No .playlist-container found");
        return;
    }
    playlistContainer.replaceChildren();

    playlistItems.items.forEach(item => {
        const playlistItem = document.createElement('div');
        playlistItem.className = 'playlist-item';
        playlistItem.id = item.uuid;
        playlistItem.innerHTML = `
            <div class="playlist-item-handle">☰</div>
            <div class="playlist-item-name">${item.name}</div>
            <div class="playlist-item-delete">
                <i class="fa-regular fa-trash-can" onclick=deleteItem('${item.uuid}')></i>
            </div>
        `;
        playlistContainer.appendChild(playlistItem);
    });
    Sortable.create(
        playlistContainer,
        {
            draggable: ".playlist-item",
            animation: 150,
            onUpdate: playlistItemChange,
            onStart: playlistDragStart,
            onEnd: playlistDragEnd,
        }
    );
}

function deleteItem() {
    console.log("Delete item pressed");
}

function loadAppParams(app_index) {

    const app = apps[app_index];

    const popup = getPopup();
    const container = popup.querySelector(".parameter-container");
    if (!container || !app || !app.parameters) return;

    container.replaceChildren();

    Object.entries(app.parameters).forEach(([key, value]) => {
        const paramRow = document.createElement("div");
        paramRow.className = "parameter-row";
        paramRow.dataset.key = key;

        const paramField = document.createElement("div");
        paramField.textContent = key;

        const paramForm = document.createElement("input");
        paramForm.className = "parameter-form";
        paramForm.value = value?.default ?? "";

        paramRow.appendChild(paramField);
        paramRow.appendChild(paramForm);
        container.appendChild(paramRow);
    });
}

function getPopup() {
    return document.getElementById("playlist-popup");
}

function getPlaylistContainer(){
    const element = document.querySelector(".playlist-container");
    return element;
}

function playlistItemChange(event) {
    console.log("Playlist change");
}

function playlistDragStart(event) {
    const container = getPlaylistContainer();
    const items = container.querySelectorAll(".playlist-item");
    items.forEach(item => {
        if (item.id != event.item.id){
            item.classList.add('playlist-item-hide');
        }
        else{
            const deleteButton = item.querySelector(".playlist-item-delete");
            deleteButton.style.display = "none";
        }
        
    });
}

function playlistDragEnd(event) {
    const container = getPlaylistContainer();
    const items = container.querySelectorAll(".playlist-item");
    items.forEach(item => {
        item.classList.remove('playlist-item-hide');
    });
}

// Called on Startup
document.addEventListener("DOMContentLoaded", init);