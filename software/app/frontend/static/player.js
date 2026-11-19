let playerUpdateInterval = null;
let playlistStatus = null;

function formatTime(totalSeconds) {
  const seconds = Math.max(0, Math.floor(totalSeconds));
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(remainder).padStart(2, '0')}`;
}

async function playPausePlaylist(){
    if (playlistStatus.is_active){
      currentItem = playlistStatus.currentItem;
      console.log(currentItem);
    }
    console.log(`Active Item: ${playlistStatus.is_active} - ${playlistStatus.is_active ? false : true}`)
    requestStartStop(playlistStatus.is_active ? false : true)
}

async function updatePlayerBar(){
  
    playlistStatus = await checkPlaylistStatus();
    const button = document.getElementById("playpause-btn");
    const bar = document.querySelector(".bottom-bar");
    const currentPlayerTime = bar?.querySelector("#player-current-time");
    const timeElapsed = document.querySelector("#time-elapsed");
    const totalTime = document.querySelector("#total-time");
    const playerItemName = bar?.querySelector(".player-current-item");
    const playerCurrentIndex = document.querySelector("#active-item");
    const playerTotalIndex = document.querySelector("#total-items");

    if (!playlistStatus.is_active){
      // Stop symbol
      button.textContent = String.fromCodePoint("9658");
      
      if (playlistStatus.numItems === 0){
        button.classList.remove('active');
        button.classList.add("inactive");
        return;
      }
    }
    
    button.classList.remove('inactive');
    button.classList.add("active");

    // Start symbol
    button.textContent = String.fromCodePoint(playlistStatus.is_active ? "9209" : "9658");

    const currentEntry = playlistStatus.currentEntry;
    playerItemName.textContent = currentEntry.item.name;
    playerCurrentIndex.textContent = currentEntry.index + 1;
    playerTotalIndex.textContent = playlistStatus.numItems;
    const durationSeconds =
      currentEntry.duration.minutes * 60 + currentEntry.duration.seconds;
    totalTime.textContent = formatTime(durationSeconds);

    if (playlistStatus.currentEntryTime != null){
      timeElapsed.textContent = formatTime(playlistStatus.currentEntryTime.elapsed);
    }
    
}

async function checkPlaylistStatus() {
  const response = await fetch("/api/v1/playlist/status");
  if (!response.ok){
    throw new Error("playlist status error");
  } 
  return await response.json();
};

async function requestStartStop(start){
  const endpoint = start ? "start": "stop";
  console.log(`Endpoint: ${endpoint}`);
  const response = await fetch(`/api/v1/playlist/${endpoint}`, {
    method: 'POST',
    headers: {"Content-Type": "application/json"},
  });
  if (!response.ok){
    throw new Error("Bad start/stop request");
  }
  const responseData = await response.json();
  console.log(responseData);
}

updatePlayerBar();
playerUpdateInterval = setInterval(() => {
  updatePlayerBar()}, 500
);