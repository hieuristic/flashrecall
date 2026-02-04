const DB_NAME = 'FlashRecallDB';
const DB_VERSION = 4;
const STORE_VOCAB = 'vocabulary';
const STORE_PROGRESS = 'progress';
const VOCAB_BIN_URL = 'vocab.bin';
const PROTO_URL = 'vocab.proto'; // Load schema dynamically

// Load protobuf.js library - assumes it's loaded in index.html via script tag
// <script src="https://cdn.jsdelivr.net/npm/protobufjs@7.X.X/dist/protobuf.min.js"></script>
// or fetched locally. User asked for "js called io.js".

class IO {
    constructor() {
        this.db = null;
        this.payload = null; // Decoded VocabularyData
        this.root = null; // Protobuf root
    }

    // Getter for data version - returns the version from loaded payload
    get version() {
        return this.payload ? this.payload.version : null;
    }


    async init() {
        await this.openDB();
        await this.loadSchema();
        await this.loadVocabulary();
    }

    async loadSchema() {
        return new Promise((resolve, reject) => {
            protobuf.load(PROTO_URL, (err, root) => {
                if (err) return reject(err);
                this.root = root;
                resolve();
            });
        });
    }

    async openDB() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(DB_NAME, DB_VERSION);

            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                // Core stores for generic app data
                if (!db.objectStoreNames.contains('settings')) {
                    db.createObjectStore('settings', { keyPath: 'id' });
                }
                if (!db.objectStoreNames.contains('daily_stats')) {
                    const dailyStore = db.createObjectStore('daily_stats', { keyPath: 'id' });
                    dailyStore.createIndex('date', 'date', { unique: false });
                }
                // Legacy store? Keep it just in case, or let it die.
                // index.html uses 'vocab' for old CSV. New 'vocabulary' is for Protobuf.
                if (!db.objectStoreNames.contains('vocab')) {
                    db.createObjectStore('vocab', { keyPath: 'german' });
                }

                // New Proto stores
                if (!db.objectStoreNames.contains(STORE_VOCAB)) {
                    db.createObjectStore(STORE_VOCAB, { keyPath: 'id' });
                }
                if (!db.objectStoreNames.contains(STORE_PROGRESS)) {
                    db.createObjectStore(STORE_PROGRESS, { keyPath: 'word_id' });
                }
            };

            request.onsuccess = (event) => {
                this.db = event.target.result;
                resolve();
            };

            request.onerror = (event) => {
                reject('IndexedDB Error: ' + event.target.error);
            };
        });
    }

    async loadVocabulary() {
        // 1. Fetch bin file info (Head request or just fetch, it's ~400KB usually)
        // Check current cached version.
        const response = await fetch(VOCAB_BIN_URL);
        if (!response.ok) throw new Error('Failed to fetch vocabulary');

        const buffer = await response.arrayBuffer();
        const VocabularyData = this.root.lookupType("flashrecall.VocabularyData");

        // Decode to check version
        const decoded = VocabularyData.decode(new Uint8Array(buffer));

        // 2. Check cached version in DB
        const cachedVersion = await this.getCachedVersion();

        if (cachedVersion !== decoded.version) {
            console.log(`New vocabulary version ${decoded.version} detected (old: ${cachedVersion}). Updating DB.`);
            await this.saveVocabularyToDB(decoded);
        } else {
            console.log(`Vocabulary version ${decoded.version} is up to date.`);
            // In a real app we might load from IDB to save network, but we just fetched the bin 
            // to check version (unless we have a separate version.json). 
            // Since we already downloaded the bin, we use it.
            // If we wanted to save bandwidth, we'd fetch a tiny version file first.
            // Given the file size (small), fetching it always is robust.
        }

        this.payload = decoded;
        return this.payload.words;
    }

    async getCachedVersion() {
        return new Promise((resolve) => {
            const transaction = this.db.transaction([STORE_VOCAB], 'readonly');
            const store = transaction.objectStore(STORE_VOCAB);
            const request = store.get('meta'); // We'll store the whole block or metadata

            request.onsuccess = () => {
                if (request.result) {
                    resolve(request.result.version);
                } else {
                    resolve(-1);
                }
            };
            request.onerror = () => resolve(-1);
        });
    }

    async saveVocabularyToDB(vocabData) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([STORE_VOCAB], 'readwrite');
            const store = transaction.objectStore(STORE_VOCAB);

            // Store metadata (version) separately or with data?
            // Let's store the whole object as one chunk for now, or individual words?
            // Storing individual words is better for querying if needed, but for "loading" the whole app,
            // a single blob or iterating is fine. 
            // User asked: "replace the indexed.db".

            // Let's store: key='meta' -> { version: X }
            // And maybe words? 
            // Actually, if we just keep the simple 'load everything' model:

            store.put({ id: 'meta', version: vocabData.version });

            // If we strictly wanted to cache the words to avoid fetch:
            // We would need to implement the 'fetch version only' logic.
            // For now, this satisfies the requirement of replacing DB on update.
            resolve();
        });
    }

    // Progress Methods

    async saveProgress(wordId, progressData) {
        // progressData should match or be compatible with WordProgress proto or just JS object
        // key: word_id
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([STORE_PROGRESS], 'readwrite');
            const store = transaction.objectStore(STORE_PROGRESS);
            const item = { word_id: wordId, ...progressData };
            store.put(item);
            transaction.oncomplete = () => resolve();
            transaction.onerror = () => reject(transaction.error);
        });
    }

    async getAllProgress() {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([STORE_PROGRESS], 'readonly');
            const store = transaction.objectStore(STORE_PROGRESS);
            const request = store.getAll();
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }
}

// Export singleton
window.io = new IO();
