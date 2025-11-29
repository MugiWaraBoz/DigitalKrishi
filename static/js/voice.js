// Global TTS state so both DOM handlers and global functions can access
let ttsQueue = [];
let isSpeakingQueue = false;
let isQueuePaused = false;
let currentAudio = null;

document.addEventListener('DOMContentLoaded', function () {
	// Initialize elements
	const statusEl = document.getElementById('status');
	const listenBtn = document.getElementById('listenBtn');
	const clearBtn = document.getElementById('clearBtn');
	const speakBtn = document.getElementById('speakBtn');
	const stopSpeakBtn = document.getElementById('stopSpeakBtn');
	const transcriptEl = document.getElementById('transcript');

	if (!statusEl || !listenBtn || !clearBtn || !speakBtn || !transcriptEl || !stopSpeakBtn) {
		console.warn('voice.js: missing required DOM elements, skipping initialization');
		return;
	}

	// Feature detect
	const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
	if (!SpeechRecognition) {
		statusEl.textContent = 'স্ট্যাটাস: আপনার ব্রাউজার Web Speech API সমর্থন করে না। (Use Chrome/Edge)';
		listenBtn.disabled = speakBtn.disabled = true;
		return;
	}

	const recognition = new SpeechRecognition();
	recognition.lang = 'bn-BD';
	recognition.interimResults = true;
	recognition.continuous = false; // stop automatically when user stops speaking

	let finalTranscript = '';
	let isListening = false;


	recognition.onstart = () => {
		isListening = true;
		statusEl.textContent = 'স্ট্যাটাস: শুনছি...';
		listenBtn.textContent = 'শুনছি... ⏺️';
		listenBtn.classList.add('btn-danger');
		listenBtn.classList.remove('btn-primary');
	};

	recognition.onend = () => {
		isListening = false;
		statusEl.textContent = 'স্ট্যাটাস: থেমে গেছে';
		listenBtn.textContent = 'শুনুন (Listen) 🎤';
		listenBtn.classList.remove('btn-danger');
		listenBtn.classList.add('btn-primary');

		// When recognition ends (auto-stop after user stops talking), process final transcript
		const text = finalTranscript.trim();
		if (text) {
			transcriptEl.value = text;
			// clear buffer before sending so we don't resend
			finalTranscript = '';
			processVoiceQuestion(text);
		}
	};

	recognition.onerror = (e) => {
		console.error('recognition error', e);
		statusEl.textContent = 'স্ট্যাটাস: ত্রুটি — ' + (e.error || e.message || 'unknown');
		isListening = false;
		listenBtn.textContent = 'শুনুন (Listen) 🎤';
		listenBtn.classList.remove('btn-danger');
		listenBtn.classList.add('btn-primary');
	};

	recognition.onresult = (event) => {
		let interim = '';
		for (let i = event.resultIndex; i < event.results.length; ++i) {
			const transcript = event.results[i][0].transcript;
			if (event.results[i].isFinal) {
				finalTranscript += transcript + ' ';
			} else {
				interim += transcript;
			}
		}
		transcriptEl.value = (finalTranscript + interim).trim();
	};

	listenBtn.addEventListener('click', () => {
		if (!isListening) {
			finalTranscript = '';
			try { recognition.start(); } catch (e) { console.warn('recognition.start', e); }
		} else {
			try { recognition.stop(); } catch (e) { console.warn('recognition.stop', e); }
		}
	});

	clearBtn.addEventListener('click', () => {
		finalTranscript = '';
		transcriptEl.value = '';
	});

	// Stop any playing speech (native or server audio)
	stopSpeakBtn.addEventListener('click', () => {
		// Stop native speechSynthesis
		try {
			if (window.speechSynthesis && (window.speechSynthesis.speaking || window.speechSynthesis.pending)) {
				window.speechSynthesis.cancel();
			}
		} catch (e) { console.warn('speechSynthesis cancel error', e); }

		// Stop server audio playback
		if (currentAudio) {
			try {
				currentAudio.pause();
				try { URL.revokeObjectURL(currentAudio.src); } catch (e) {}
			} catch (e) { console.warn('stop currentAudio', e); }
			currentAudio = null;
		}

		// Clear the queue as well
		ttsQueue = [];
		isSpeakingQueue = false;
		// update UI indicators if present
		try { updateQueueUI(); } catch (e) {}
		const pb = document.getElementById('pauseQueueBtn'); if (pb) pb.textContent = 'Pause Queue';
		isQueuePaused = false;
		statusEl.textContent = 'স্ট্যাটাস: উচ্চারণ বাতিল করা হয়েছে';
	});

	// Speech synthesis (bn-BD) — wait for voices to load
	function getBanglaVoice() {
		const voices = speechSynthesis.getVoices() || [];
		let v = voices.find(v => v.lang && v.lang.toLowerCase().startsWith('bn'));
		if (!v) v = voices.find(v => /bangla|bengali/i.test(v.name));
		return v || null;
	}

	let cachedVoice = null;
	function refreshVoices() {
		cachedVoice = getBanglaVoice();
	}

	if (typeof speechSynthesis !== 'undefined') {
		refreshVoices();
		if (typeof speechSynthesis.onvoiceschanged !== 'undefined') {
			speechSynthesis.onvoiceschanged = refreshVoices;
		}
	}

	function speakText(text) {
		if (!text || !text.trim()) return;
		try {
			const utter = new SpeechSynthesisUtterance(text);
			utter.lang = 'bn-BD';
			utter.rate = 1;
			utter.pitch = 1;
			if (cachedVoice) utter.voice = cachedVoice;
			utter.onstart = () => statusEl.textContent = 'স্ট্যাটাস: উচ্চারণ চলছে...';
			utter.onend = () => statusEl.textContent = 'স্ট্যাটাস: উচ্চারণ শেষ';
			utter.onerror = (e) => {
				console.error('synthesis error', e);
				statusEl.textContent = 'স্ট্যাটাস: উচ্চারণ ত্রুটি';
			};
			speechSynthesis.cancel(); // stop previous
			speechSynthesis.speak(utter);
		} catch (e) {
			console.error('speakText failed', e);
			statusEl.textContent = 'স্ট্যাটাস: উচ্চারণ ব্যর্থ হয়েছে';
		}
	}

	speakBtn.addEventListener('click', () => {
		// Manual trigger: send current transcript to AI and enqueue reply
		const question = transcriptEl.value && transcriptEl.value.trim();
		if (!question) {
			statusEl.textContent = 'স্ট্যাটাস: প্রথমে কিছু বলুন বা টেক্সট লিখুন।';
			return;
		}
		processVoiceQuestion(question);
	});
});

// Helper: send question to /api/ai/voice-question and handle response
async function processVoiceQuestion(question) {
	const statusEl = document.getElementById('status');
	const answerEl = document.getElementById('answer');
	if (!question || !question.trim()) return;

	try {
		statusEl.textContent = 'স্ট্যাটাস: আপনার প্রশ্ন প্রক্রিয়া করা হচ্ছে...';

		const res = await fetch('/api/ai/voice-question', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ question })
		});

		if (!res.ok) {
			const err = await res.json().catch(() => ({}));
			statusEl.textContent = 'স্ট্যাটাস: প্রশ্ন প্রক্রিয়া ব্যর্থ: ' + (err.error || res.statusText);
			return;
		}

		const data = await res.json();
		const rawAnswer = data.answer || '(কোনো উত্তর পাওয়া যায়নি)';
		const answer = stripAsterisks(rawAnswer);
		if (answerEl) answerEl.textContent = answer;
		statusEl.textContent = 'স্ট্যাটাস: উত্তর পাওয়া গেছে।';

		// Enqueue the sanitized answer so multiple replies play sequentially
		enqueueSpeak(answer);
		addToHistory(question, answer);
	} catch (e) {
		console.error('processVoiceQuestion error', e);
		statusEl.textContent = 'স্ট্যাটাস: নেটওয়ার্ক ত্রুটি';
	}
}

// Add text to the TTS queue and start playback if idle
function enqueueSpeak(text) {
	if (!text || !text.trim()) return;
	ttsQueue.push(text);
	updateQueueUI();
	// start playback if not already speaking and not paused
	if (!isSpeakingQueue && !isQueuePaused) {
		playNextInQueue();
	}
}

// Play next item in the queue sequentially
async function playNextInQueue() {
	if (isSpeakingQueue) return;
	if (!ttsQueue.length) return;
	isSpeakingQueue = true;
	const statusEl = document.getElementById('status');

	while (ttsQueue.length) {
		if (isQueuePaused) break;
		const text = ttsQueue.shift();
		updateQueueUI();
		try {
			statusEl.textContent = 'স্ট্যাটাস: উচ্চারণ কিউ থেকে বাজানো হচ্ছে...';
			// speakAnswer resolves when the utterance or audio finishes
			await speakAnswer(text);
		} catch (e) {
			console.warn('playNextInQueue error', e);
		}
		// small gap between items
		await new Promise(r => setTimeout(r, 300));
	}

	isSpeakingQueue = false;
	updateQueueUI();
	statusEl.textContent = 'স্ট্যাটাস: উত্তর শেষ';
}

// Try native speechSynthesis first, otherwise fetch server TTS (/api/tts)
async function speakAnswer(text) {
	const statusEl = document.getElementById('status');
	if (!text || !text.trim()) return;

	// Use cachedVoice if present
	if (window.speechSynthesis && window.speechSynthesis.getVoices) {
		// Ensure voices have time to load (short wait) to prefer native Bangla if available
		await ensureVoicesLoaded(500);
		const voices = window.speechSynthesis.getVoices() || [];
		const banglaVoice = voices.find(v => v.lang && v.lang.toLowerCase().startsWith('bn'))
			|| voices.find(v => /bengali|bangla/i.test(v.name || ''));

		if (banglaVoice) {
			// Speak using native voice
			return new Promise((resolve) => {
				try {
					const u = new SpeechSynthesisUtterance(text);
					u.lang = banglaVoice.lang || 'bn-BD';
					u.voice = banglaVoice;
					u.rate = 1;
					u.onstart = () => { statusEl.textContent = 'স্ট্যাটাস: উচ্চারণ চলছে...'; };
					u.onend = () => { statusEl.textContent = 'স্ট্যাটাস: উচ্চারণ শেষ'; resolve(); };
					u.onerror = (e) => { console.error('synth error', e); statusEl.textContent = 'স্ট্যাটাস: উচ্চারণ ত্রুটি'; resolve(); };
					window.speechSynthesis.cancel();
					window.speechSynthesis.speak(u);
				} catch (e) {
					console.error('native speak failed', e);
					serverSpeakFallback(text).then(resolve);
				}
			});
		}
	}

	// No native Bangla voice — fallback to server-side TTS
	return serverSpeakFallback(text);
}

async function serverSpeakFallback(text) {
	const statusEl = document.getElementById('status');
	try {
		statusEl.textContent = 'স্ট্যাটাস: সার্ভার TTS চালু করা হচ্ছে...';
		const resp = await fetch('/api/tts', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ text, lang: 'bn' })
		});
		if (!resp.ok) {
			statusEl.textContent = 'স্ট্যাটাস: সার্ভার TTS ব্যর্থ';
			return;
		}
		const blob = await resp.blob();
		const url = URL.createObjectURL(blob);
		const audio = new Audio(url);
		// store global reference so it can be stopped by user
		currentAudio = audio;
		audio.onended = () => { try { URL.revokeObjectURL(url); } catch (e) {} currentAudio = null; statusEl.textContent = 'স্ট্যাটাস: উচ্চারণ শেষ'; };
		audio.onerror = () => { try { URL.revokeObjectURL(url); } catch (e) {} currentAudio = null; statusEl.textContent = 'স্ট্যাটাস: অডিও প্লে ব্যর্থ'; };
		await audio.play().catch(e => { console.warn('audio play failed', e); statusEl.textContent = 'স্ট্যাটাস: প্লে ব্লক হওয়া হয়েছে'; currentAudio = null; });
	} catch (e) {
		console.error('serverSpeakFallback error', e);
		statusEl.textContent = 'স্ট্যাটাস: TTS ত্রুটি';
	}
}
// Helper: queue UI and conversation history (localStorage)
function updateQueueUI() {
	try {
		const queueCountEl = document.getElementById('queueCount');
		const queueListEl = document.getElementById('queueList');
		if (queueCountEl) queueCountEl.textContent = String(ttsQueue.length);
		if (!queueListEl) return;
		queueListEl.innerHTML = '';
		for (let i = 0; i < ttsQueue.length; i++) {
			const li = document.createElement('li');
			li.className = 'list-group-item small';
			li.textContent = ttsQueue[i].slice(0, 160);
			queueListEl.appendChild(li);
		}
	} catch (e) { /* ignore */ }
}

function loadHistory() {
	try {
		const raw = localStorage.getItem('voice_history_v1');
		return raw ? JSON.parse(raw) : [];
	} catch (e) { return []; }
}

function saveHistory(arr) {
	try { localStorage.setItem('voice_history_v1', JSON.stringify(arr)); } catch (e) {}
}

function renderHistory() {
	try {
		const historyListEl = document.getElementById('historyList');
		if (!historyListEl) return;
		const arr = loadHistory();
		historyListEl.innerHTML = '';
		arr.slice().reverse().forEach(item => {
			const div = document.createElement('div');
			div.className = 'list-group-item';
			div.innerHTML = '<strong>Q:</strong> ' + escapeHtml(item.q) + '<br><strong>A:</strong> ' + escapeHtml(item.a);
			historyListEl.appendChild(div);
		});
	} catch (e) { console.warn(e); }
}

function addToHistory(q, a) {
	try {
		const arr = loadHistory();
		arr.push({ q: q || '', a: a || '', ts: Date.now() });
		saveHistory(arr);
		renderHistory();
	} catch (e) { console.warn(e); }
}

function escapeHtml(str) {
	return String(str || '').replace(/[&<>"']/g, function (m) { return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]; });
}

// Remove asterisks and other simple markdown noise we don't want to present or speak
function stripAsterisks(text) {
	if (!text && text !== '') return '';
	try {
		// remove all asterisks, and trim extra whitespace
		return String(text).replace(/\*/g, '').replace(/\s+/g, ' ').trim();
	} catch (e) {
		return String(text || '');
	}
}

// Wire up simple UI buttons (they may be missing on older templates)
document.addEventListener('DOMContentLoaded', function () {
	try {
		const pauseBtn = document.getElementById('pauseQueueBtn');
		const clearQueueBtn = document.getElementById('clearQueueBtn');
		const clearHistoryBtn = document.getElementById('clearHistoryBtn');
		if (pauseBtn) {
			pauseBtn.addEventListener('click', function () {
				isQueuePaused = !isQueuePaused;
				pauseBtn.textContent = isQueuePaused ? 'Resume Queue' : 'Pause Queue';
				if (!isQueuePaused && !isSpeakingQueue && ttsQueue.length) {
					playNextInQueue();
				}
			});
		}
		if (clearQueueBtn) {
			clearQueueBtn.addEventListener('click', function () { ttsQueue = []; updateQueueUI(); });
		}
		if (clearHistoryBtn) {
			clearHistoryBtn.addEventListener('click', function () { try { localStorage.removeItem('voice_history_v1'); } catch (e) {} renderHistory(); });
		}
	} catch (e) { console.warn(e); }
	// initial render
	try { updateQueueUI(); renderHistory(); } catch (e) {}
});

// Wait up to `timeout` ms for speechSynthesis voices to be available
function ensureVoicesLoaded(timeout = 500) {
	return new Promise((resolve) => {
		if (!window.speechSynthesis || !window.speechSynthesis.getVoices) return resolve([]);
		let voices = window.speechSynthesis.getVoices();
		if (voices && voices.length) return resolve(voices);

		let resolved = false;
		function onChanged() {
			if (resolved) return;
			voices = window.speechSynthesis.getVoices();
			if (voices && voices.length) {
				resolved = true;
				window.speechSynthesis.onvoiceschanged = null;
				resolve(voices);
			}
		}
		window.speechSynthesis.onvoiceschanged = onChanged;
		setTimeout(() => {
			if (!resolved) {
				resolved = true;
				window.speechSynthesis.onvoiceschanged = null;
				resolve(window.speechSynthesis.getVoices() || []);
			}
		}, timeout);
	});
}
