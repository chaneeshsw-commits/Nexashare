function onScanSuccess(decodedText) {
    window.location.href = decodedText;
}

if (document.getElementById("reader")) {
    const scanner = new Html5QrcodeScanner("reader", {
        fps: 10,
        qrbox: 250
    });
    scanner.render(onScanSuccess);
}

if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/service-worker.js');
}