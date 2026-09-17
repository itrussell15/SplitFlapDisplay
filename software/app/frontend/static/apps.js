
let appsAvailable = {};

async function init() {
    console.log(`Starting page`);
    const appsRequest = await fetch("/api/v1/apps/list");
    if (!appsRequest.ok) throw new Error(`App fetch failed: ${appsRequest.status}`);
    appsAvailable = await appsRequest.json();
    console.log(appsAvailable);
    const appsList = Array.isArray(appsAvailable.apps) ? appsAvailable.apps : [];
    appsList.forEach(app => createAppCard(app));

}

function createAppCard(app_info){
    const container = document.querySelector('.card-container');
    if (!container) {
        console.warn('No .card-container element found to append app cards');
        return;
    }

    // Create card
    const card = document.createElement("div");
    card.className = "section-card section-card-app";

    const appIconContainer = document.createElement("div");
    appIconContainer.className = "app-icon-container";
    
    const appIcon = document.createElement("img");
    const img = document.createElement("img");
    img.class_name = "app-icon";
    if (app_info.app_image){
        img.src = app_info.app_image;
        img.style.width = '100%';
        img.style.height = '100%';
    }
    else{
        img.style.display = "none";
    }

    const appContentContainer = document.createElement("div");
    appContentContainer.className = "app-content-container";
    appContentContainer.innerHTML = `
        <h3 class="section-title">${app_info.name}</h3>
        <p class="section-description">${app_info.description || ''}</p>
    `

    appIconContainer.appendChild(img);
    card.appendChild(appIconContainer);
    card.appendChild(appContentContainer);

    container.appendChild(card);

}

// Called on Startup
document.addEventListener("DOMContentLoaded", init);