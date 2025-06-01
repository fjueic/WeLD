// Track all active mask elements and their observers
const maskElements = new Map(); // Stores { element: { rect, observers } }

// Throttle function to limit update frequency
function throttle(fn, delay) {
	let lastCall = 0;
	return (...args) => {
		const now = Date.now();
		if (now - lastCall >= delay) {
			fn(...args);
			lastCall = now;
		}
	};
}

// Send mask data to GTK
const sendMaskData = throttle(() => {
	const masks = Array.from(maskElements.keys()).map((el) => {
		const rect = el.getBoundingClientRect();
		return [rect.left, rect.top, rect.width, rect.height];
	});

	// window.webkit.messageHandlers.pybridge.postMessage(
	// 	JSON.stringify({
	// 		type: "inputMask",
	// 		masks: masks.filter((m) => m[2] !== 0 && m[3] !== 0),
	// 	}),
	// );
	window.weld({
		type: "inputMask",
		masks: masks.filter((m) => m[2] !== 0 && m[3] !== 0),
	});
}, 100); // Throttle to 10fps max

// Check for element changes
function checkElementChanges(element) {
	const prevRect = maskElements.get(element)?.rect;
	const currentRect = element.getBoundingClientRect();

	if (
		!prevRect ||
		currentRect.left !== prevRect.left ||
		currentRect.top !== prevRect.top ||
		currentRect.width !== prevRect.width ||
		currentRect.height !== prevRect.height
	) {
		maskElements.set(element, { rect: currentRect });
		sendMaskData();
	}
}

// Set up observers for a single mask element
function observeElement(element) {
	if (maskElements.has(element)) return;
	element.addEventListener("mouseleave", () => {
		window.weld({
			type: "applyInputMask",
		});
		// window.webkit.messageHandlers.pybridge.postMessage(
		// 	JSON.stringify({
		// 		type: "applyInputMask",
		// 	}),
		// );
	});
	element.addEventListener("mouseenter", () => {
		window.weld({
			type: "removeInputMask",
		});
		// window.webkit.messageHandlers.pybridge.postMessage(
		// 	JSON.stringify({
		// 		type: "removeInputMask",
		// 	}),
		// );
	});

	const rect = element.getBoundingClientRect();
	maskElements.set(element, { rect });

	// 1. ResizeObserver for size changes
	const resizeObserver = new ResizeObserver(() => checkElementChanges(element));
	resizeObserver.observe(element);

	// 2. MutationObserver for attribute changes (e.g., style/class)
	const mutationObserver = new MutationObserver(() =>
		checkElementChanges(element),
	);
	mutationObserver.observe(element, {
		attributes: true,
		attributeFilter: ["style", "class"],
	});

	// 3. Lightweight polling for transforms (throttled in checkElementChanges)
	const poll = () => {
		checkElementChanges(element);
		requestAnimationFrame(poll);
	};
	poll();

	// Store observers for cleanup
	maskElements.get(element).observers = {
		resizeObserver,
		mutationObserver,
	};
}

// Clean up observers for a single element
function unobserveElement(element) {
	if (!maskElements.has(element)) return;

	const { observers } = maskElements.get(element);
	observers.resizeObserver.disconnect();
	observers.mutationObserver.disconnect();

	maskElements.delete(element);
	sendMaskData(); // Update GTK after removal
}

// Initialize: Observe all existing .mask elements
//
document.querySelectorAll(".mask").forEach(observeElement);

// Watch for dynamically added/removed .mask elements
const domObserver = new MutationObserver((mutations) => {
	mutations.forEach((mutation) => {
		mutation.addedNodes.forEach((node) => {
			if (node.nodeType === Node.ELEMENT_NODE) {
				if (node.classList.contains("mask")) observeElement(node);
				node.querySelectorAll?.(".mask").forEach(observeElement);
			}
		});
		mutation.removedNodes.forEach((node) => {
			if (node.nodeType === Node.ELEMENT_NODE) {
				if (node.classList.contains("mask")) unobserveElement(node);
				node.querySelectorAll?.(".mask").forEach(unobserveElement);
			}
		});
	});
	sendMaskData();
});
domObserver.observe(document.body, {
	subtree: true,
	childList: true,
});

function unobserveElement(element) {
	if (!maskElements.has(element)) return;

	const { observers } = maskElements.get(element);
	observers?.resizeObserver?.disconnect();
	observers?.mutationObserver?.disconnect();

	maskElements.delete(element);
	sendMaskData(); // Re-send after removal
}

function cleanup() {
	domObserver.disconnect();
	maskElements.forEach((_, element) => unobserveElement(element));
}
