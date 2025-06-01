function updateHeight() {
	const height = document.body.offsetHeight;
	const width = document.body.offsetWidth;
	// window.webkit.messageHandlers.pybridge.postMessage(
	// 	JSON.stringify({ type: "syncDimension", height: height, width: width }),
	// );
	window.weld({ type: "syncDimension", height: height, width: width });
}
new ResizeObserver(updateHeight).observe(document.body);
updateHeight();
