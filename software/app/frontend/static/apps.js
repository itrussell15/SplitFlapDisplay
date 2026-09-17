
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

function createAppCard(app_info)
{
    const container = document.querySelector('.card-container');
    if (!container) {
        console.warn('No .card-container element found to append app cards');
        return;
    }

    const image_url = app_info.app_image;

    if (image_url){
        const img = document.createElement("img");
        img.class_name = "app-icon";
        img.src = image_url;
        iconContainer.appendChild(img);
    }

    const card = document.createElement("div");
    card.className = "section-card section-card-app";
    card.innerHTML = `
        <div class=app-icon-container>
            <img class=app-icon src="${app_info.app_image}">  
        </div>
        <div class=app-content-container>
            <h3 class="section-title">${app_info.name}</h3>
            <p class="section-description">${app_info.description || ''}</p>
        </div>
    `;

    container.appendChild(card);
}

// Called on Startup
document.addEventListener("DOMContentLoaded", init);