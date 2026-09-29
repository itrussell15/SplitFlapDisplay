
let apps = [];
let defaultApp = null;
let selectedIndex = 0;

async function init()
{   
    await createSelectItems();
    defaultApp = apps[0];
    console.log(`Default App: ${defaultApp.name}`);
    const container = document.querySelector('.playlist-container');
    if (!container){
        console.error("No .playlist-container found");
        return;
    }
    Sortable.create(container, { draggable: ".playlist-item", animation: 150});
    

    const addItemButton = document.getElementById('add-item');
    const createItemButton = document.getElementById('popup-create-item')
    const popup = getPopup();
    const popupWrapper = document.querySelector('.popup-wrapper');
    
    if (!addItemButton || !popup) return;

    // Show popup
    addItemButton.addEventListener("click", (event) => {
        event.stopPropagation();
        popupWrapper.style.display = popupWrapper.style.display === 'block' ? 'none' : 'block';
    });

    // Cancel popup when clicking outside popup
    popupWrapper.addEventListener("click", (event) => {
        const clickedInsidePopup = popup.contains(event.target);
        const clickedButton = addItemButton.contains(event.target);

        if (!clickedInsidePopup && !clickedButton){
            popupWrapper.style.display = "none"
        }
    });

    // Close popup after button press
    createItemButton.addEventListener("click", (event) => {
        if (createItem()){
            popupWrapper.style.display = "none";
        }
        else
        {
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

function createItem() {
    console.log("Creating Item");
    let validEntry = true;
    const entries = {};
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
        fetch 
    }
    console.log(`Valid Entry - ${validEntry}`);
    
    return validEntry;

}

function deleteItem() {
    console.log("Delete item pressed");
}

function loadAppParams(app_index) {

    const app = apps[app_index];

    const popup = getPopup();
    const container = popup.querySelector(".parameter-container");
    container.replaceChildren();

    Object.entries(app.parameters).forEach((key, n) => {
        const paramRow = document.createElement("div");
        paramRow.className = "parameter-row";
        paramRow.dataset.key = key[0];
        const paramField = document.createElement("div");
        const paramForm = document.createElement("input");
        paramForm.className = "parameter-form";

        paramField.textContent = `${key[0]}`;
        paramForm.value = key[1].default;

        paramRow.appendChild(paramField);
        paramRow.appendChild(paramForm);

        container.appendChild(paramRow);
    });
}

function getPopup() {
    return document.querySelector(".popup");
}

// Called on Startup
document.addEventListener("DOMContentLoaded", init);