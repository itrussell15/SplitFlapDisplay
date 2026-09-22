
async function init()
{   
    const container = document.querySelector('.playlist-container');
    if (!container){
        console.error("No .playlist-container found");
        return;
    }
    Sortable.create(container, { draggable: ".playlist-item", animation: 150});
    createSelectItems();

    const button = document.getElementById('add-item');
    const popup = document.querySelector('.popup-wrapper');
    if (!button || !popup) return;

    button.addEventListener("click", (event) => {
        popup.style.display = "block"
        event.stopPropagation();
    });
    popup.addEventListener("click", (event) => {
        const clickedInsidePopup = popup.contains(event.target);
        const clickedButton = button.contains(event.target);

        if (!clickedInsidePopup && !clickedButton){
            popup.style.display = "none"
        }
    });
}

async function createSelectItems(){
    const appsRequest = await fetch("/api/v1/apps/list");
    console.log(`App Options: ${appsRequest}`)
    if (!appsRequest.json()){
        console.error("Error fetching the available apps");
        return;
    }

    const apps = await appsRequest.json();
    const container = document.querySelector('.playlist-app-selector-select');
    const selector = document.createElement("select");
    
    appsRequest.foreach(app => console.log(app));
}

function createItem() {
    container = document.querySelector('.playlist-container');
    const item = document.createElement("div");
    item.className = "playlist-item";
    item.textContent = "TEST";
    container.appendChild(item);
}

function deleteItem() {
    console.log("Delete item pressed");
}


// Called on Startup
document.addEventListener("DOMContentLoaded", init);