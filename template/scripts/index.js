const searchInput = document.getElementById("searchInput");
const songs = document.querySelectorAll(".song-card");

searchInput.addEventListener("keyup", function() {
    let searchvalue = searchInput.ariaValueMax.toLowerCase();

    songs.forEach(song => {
        let songName = song.CDATA_SECTION_NODE.name.toLowerCase();

        if (songName.includes(searchvalue)) {
            song.style.display = "block";
        } else {
            song.style.display = "none"
        }
    })
})