/* Artem Sites - small vanilla JS helpers: geolocation + voice notes. */

// Fill hidden lat/lng fields on any form marked data-geo-form.
document.querySelectorAll("[data-geo-form]").forEach(function (form) {
  if (!navigator.geolocation) return;
  navigator.geolocation.getCurrentPosition(function (pos) {
    var lat = form.querySelector('[name="lat"]');
    var lng = form.querySelector('[name="lng"]');
    if (lat) lat.value = pos.coords.latitude.toFixed(6);
    if (lng) lng.value = pos.coords.longitude.toFixed(6);
    var note = form.querySelector(".geo-note");
    if (note) note.textContent = "Location captured ✓";
  }, function () {
    var note = form.querySelector(".geo-note");
    if (note) note.textContent = "Location not available (you can still save).";
  }, { timeout: 8000 });
});

// Voice note recorder: records with MediaRecorder and attaches the
// recording to the file input, so the normal form upload handles it.
(function () {
  var recBtn = document.getElementById("recBtn");
  var voiceInput = document.getElementById("voiceInput");
  var voiceStatus = document.getElementById("voiceStatus");
  if (!recBtn || !voiceInput) return;
  var mediaRecorder = null;
  var chunks = [];

  recBtn.addEventListener("click", async function () {
    if (mediaRecorder && mediaRecorder.state === "recording") {
      mediaRecorder.stop();
      recBtn.textContent = "🎙️ Record voice note";
      return;
    }
    try {
      var stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);
      chunks = [];
      mediaRecorder.ondataavailable = function (e) { chunks.push(e.data); };
      mediaRecorder.onstop = function () {
        var blob = new Blob(chunks, { type: mediaRecorder.mimeType || "audio/webm" });
        var ext = blob.type.indexOf("mp4") !== -1 ? ".mp4" : ".webm";
        var file = new File([blob], "voice-note" + ext, { type: blob.type });
        var dt = new DataTransfer();
        dt.items.add(file);
        voiceInput.files = dt.files;
        if (voiceStatus) voiceStatus.textContent = "Voice note attached ✓";
        stream.getTracks().forEach(function (t) { t.stop(); });
      };
      mediaRecorder.start();
      recBtn.textContent = "⏹️ Stop recording";
      if (voiceStatus) voiceStatus.textContent = "Recording… tap stop when done.";
    } catch (err) {
      if (voiceStatus) voiceStatus.textContent = "Microphone not available. You can upload an audio file instead.";
    }
  });
})();
