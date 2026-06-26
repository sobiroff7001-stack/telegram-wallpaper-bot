// Telegram WebApp SDK
const tg = window.Telegram?.WebApp;
if (tg) {
    tg.ready();
    tg.expand();
}

// State
let roomWidth = 4.0;
let roomLength = 4.0;
let roomHeight = 2.8;
let calcMode = 'room'; // 'room' or 'wall'
let selectedWallpaper = null;
let selectedFloor = 'wood-light';
let furnitureItems = [];
let selectedItemId = null;

// Dragging State
let isDragging = false;
let draggedItem = null;
let startX = 0;
let startY = 0;
let initialLeft = 0;
let initialTop = 0;

// Fallback catalog if products.json fails to load
const fallbackProducts = [
    {
        "category": "Panellar va 3D Oboylar",
        "items": [
            { "id": "3d-oboy-glatkiy", "name": "3D oboy korea (Glatkiy)", "priceValue": 38000, "currency": "UZS", "image_file": "wallpaper-1.jpg" },
            { "id": "3d-oboy-korea", "name": "3D oboy korea", "priceValue": 38000, "currency": "UZS", "image_file": "wallpaper-2.jpg" },
            { "id": "mat-3d-korea", "name": "Mat 3D korea", "priceValue": 38000, "currency": "UZS", "image_file": "wallpaper-4.jpg" },
            { "id": "ichanki-oboy-foil", "name": "ICHANKI oboy falgalik", "priceValue": 36000, "currency": "UZS", "image_file": "wallpaper-5.jpg" },
            { "id": "ichanki-oboy-no-foil", "name": "ICHANKI oboy falgasiz", "priceValue": 36000, "currency": "UZS", "image_file": "wallpaper-1.jpg" }
        ]
    },
    {
        "category": "Bo'yoqlar va Travertin",
        "items": [
            { "id": "travertin-oq", "name": "Travertin oq (25kg)", "priceValue": 110000, "currency": "UZS", "image_file": "paint-1.jpg" },
            { "id": "travertin-001", "name": "Travertin 001 (25kg)", "priceValue": 110000, "currency": "UZS", "image_file": "paint-2.jpg" },
            { "id": "travertin-01", "name": "Travertin 01 (25kg)", "priceValue": 110000, "currency": "UZS", "image_file": "paint-3.jpg" },
            { "id": "travertin-02", "name": "Travertin 02 (25kg)", "priceValue": 110000, "currency": "UZS", "image_file": "paint-5.jpg" }
        ]
    }
];

// Vector SVG Furniture Assets
const furnitureAssets = [
    {
        type: 'sofa',
        name: 'Divan',
        width: 130,
        height: 60,
        yPos: 65, // floor offset percentage
        svg: `<svg viewBox="0 0 150 70" xmlns="http://www.w3.org/2000/svg">
            <rect x="10" y="30" width="130" height="30" rx="10" fill="#4f46e5"/>
            <rect x="20" y="20" width="110" height="20" rx="5" fill="#6366f1"/>
            <rect x="5" y="25" width="20" height="30" rx="5" fill="#3730a3"/>
            <rect x="125" y="25" width="20" height="30" rx="5" fill="#3730a3"/>
            <rect x="15" y="55" width="15" height="12" fill="#1e1b4b"/>
            <rect x="120" y="55" width="15" height="12" fill="#1e1b4b"/>
            <path d="M30 40 h90" stroke="#3730a3" stroke-width="2"/>
        </svg>`
    },
    {
        type: 'bed',
        name: 'Karovat',
        width: 140,
        height: 70,
        yPos: 62,
        svg: `<svg viewBox="0 0 160 80" xmlns="http://www.w3.org/2000/svg">
            <rect x="10" y="10" width="140" height="15" rx="3" fill="#b45309"/>
            <rect x="15" y="25" width="130" height="40" fill="#e2e8f0"/>
            <rect x="15" y="20" width="130" height="10" rx="2" fill="#cbd5e1"/>
            <rect x="25" y="25" width="50" height="15" rx="3" fill="#f8fafc"/>
            <rect x="85" y="25" width="50" height="15" rx="3" fill="#f8fafc"/>
            <rect x="12" y="60" width="136" height="8" fill="#b45309"/>
            <rect x="15" y="68" width="12" height="12" fill="#78350f"/>
            <rect x="133" y="68" width="12" height="12" fill="#78350f"/>
        </svg>`
    },
    {
        type: 'tv',
        name: 'Televizor',
        width: 110,
        height: 90,
        yPos: 50,
        svg: `<svg viewBox="0 0 120 100" xmlns="http://www.w3.org/2000/svg">
            <rect x="5" y="70" width="110" height="25" rx="4" fill="#5c4033"/>
            <rect x="15" y="76" width="30" height="10" fill="#3e2723"/>
            <rect x="75" y="76" width="30" height="10" fill="#3e2723"/>
            <rect x="10" y="10" width="100" height="55" rx="3" fill="#1e293b" stroke="#0f172a" stroke-width="4"/>
            <rect x="12" y="12" width="96" height="51" fill="#020617"/>
            <rect x="50" y="65" width="20" height="10" fill="#0f172a"/>
        </svg>`
    },
    {
        type: 'window',
        name: 'Deraza',
        width: 90,
        height: 80,
        yPos: 20,
        svg: `<svg viewBox="0 0 100 90" xmlns="http://www.w3.org/2000/svg">
            <rect x="5" y="5" width="90" height="80" fill="none" stroke="#f1f5f9" stroke-width="6"/>
            <rect x="8" y="8" width="84" height="74" fill="rgba(186, 230, 253, 0.4)"/>
            <line x1="50" y1="5" x2="50" y2="85" stroke="#f1f5f9" stroke-width="4"/>
            <line x1="5" y1="45" x2="95" y2="45" stroke="#f1f5f9" stroke-width="4"/>
        </svg>`
    },
    {
        type: 'plant',
        name: 'Uy guli',
        width: 50,
        height: 75,
        yPos: 55,
        svg: `<svg viewBox="0 0 60 90" xmlns="http://www.w3.org/2000/svg">
            <ellipse cx="30" cy="20" rx="8" ry="15" fill="#047857" transform="rotate(-30 30 20)"/>
            <ellipse cx="30" cy="20" rx="8" ry="15" fill="#047857" transform="rotate(30 30 20)"/>
            <ellipse cx="20" cy="35" rx="10" ry="18" fill="#059669" transform="rotate(-45 20 35)"/>
            <ellipse cx="40" cy="35" rx="10" ry="18" fill="#059669" transform="rotate(45 40 35)"/>
            <ellipse cx="30" cy="45" rx="12" ry="20" fill="#10b981"/>
            <path d="M30 40 L30 75" stroke="#047857" stroke-width="3"/>
            <path d="M15 70 L45 70 L38 90 L22 90 Z" fill="#d97706"/>
        </svg>`
    },
    {
        type: 'lamp',
        name: 'Torsher',
        width: 40,
        height: 100,
        yPos: 40,
        svg: `<svg viewBox="0 0 50 120" xmlns="http://www.w3.org/2000/svg">
            <line x1="25" y1="30" x2="25" y2="115" stroke="#d97706" stroke-width="3"/>
            <path d="M15 115 L35 115 L38 120 L12 120 Z" fill="#78350f"/>
            <path d="M10 30 L40 30 L35 10 L15 10 Z" fill="#fef08a"/>
            <polygon points="25,30 -5,80 55,80" fill="rgba(254, 240, 138, 0.2)"/>
        </svg>`
    },
    {
        type: 'painting',
        name: 'Kartina',
        width: 60,
        height: 50,
        yPos: 20,
        svg: `<svg viewBox="0 0 70 60" xmlns="http://www.w3.org/2000/svg">
            <rect x="5" y="5" width="60" height="50" fill="#3b82f6" stroke="#b45309" stroke-width="5"/>
            <circle cx="35" cy="25" r="12" fill="#f59e0b"/>
            <path d="M5 45 L25 30 L45 40 L65 30 L65 50 L5 50 Z" fill="#10b981"/>
        </svg>`
    }
];

// Floor styling maps (using CSS gradients instead of local assets for guaranteed loading)
const floorStyles = {
    'wood-light': {
        name: 'Och Laminat',
        css: 'repeating-linear-gradient(90deg, #d7ccc8, #d7ccc8 24px, #bcaaa4 25px)'
    },
    'wood-dark': {
        name: 'To\'q Laminat',
        css: 'repeating-linear-gradient(90deg, #5d4037, #5d4037 24px, #3e2723 25px)'
    },
    'tile-gray': {
        name: 'Kafel',
        css: 'repeating-linear-gradient(0deg, transparent, transparent 30px, #94a3b8 31px), repeating-linear-gradient(90deg, #cbd5e1, #cbd5e1 30px, #94a3b8 31px)'
    },
    'carpet': {
        name: 'Gilamli pol',
        css: 'radial-gradient(circle, #64748b 20%, transparent 20%), radial-gradient(circle, #64748b 20%, transparent 20%); background-size: 4px 4px; background-position: 0 0, 2px 2px; background-color: #475569;'
    }
};

// Fallback CSS wallpaper graphics if the catalog images don't load or aren't set
const fallbackWallpaperCSS = {
    '3d-oboy-glatkiy': 'linear-gradient(135deg, #f8fafc 25%, transparent 25%) -10px 0/ 20px 20px, linear-gradient(225deg, #f8fafc 25%, transparent 25%) -10px 0/ 20px 20px, linear-gradient(45deg, #f8fafc 25%, transparent 25%) 0 0/ 20px 20px, linear-gradient(315deg, #f8fafc 25%, #f1f5f9 25%) 0 0/ 20px 20px',
    '3d-oboy-korea': 'radial-gradient(circle, #cbd5e1 10%, transparent 11%), radial-gradient(circle, #e2e8f0 10%, transparent 11%); background-size: 20px 20px; background-position: 0 0, 10px 10px; background-color: #f1f5f9;',
    'mat-3d-korea': 'linear-gradient(45deg, #cbd5e1 25%, transparent 25%), linear-gradient(-45deg, #cbd5e1 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #cbd5e1 75%), linear-gradient(-45deg, transparent 75%, #cbd5e1 75%); background-size: 20px 20px; background-position: 0 0, 0 10px, 10px -10px, -10px 0px; background-color: #f8fafc;',
    'ichanki-oboy-foil': 'repeating-linear-gradient(45deg, #fef08a, #fef08a 8px, #fde047 8px, #fde047 16px)',
    'ichanki-oboy-no-foil': '#fef3c7',
    'travertin-oq': '#f8fafc',
    'travertin-001': '#fafaf9',
    'travertin-01': '#f5f5f4',
    'travertin-02': '#ebd9c8'
};

// DOM Elements
const roomCanvas = document.getElementById('room-canvas');
const roomWall = document.getElementById('room-wall');
const roomFloor = document.getElementById('room-floor');
const furnitureLayer = document.getElementById('furniture-layer');
const tabButtons = document.querySelectorAll('.tab-btn');
const tabContents = document.querySelectorAll('.tab-content');
const btnSubmit = document.getElementById('btn-submit');

// Inputs & Value displays
const inputWidth = document.getElementById('input-width');
const inputLength = document.getElementById('input-length');
const inputHeight = document.getElementById('input-height');
const valWidth = document.getElementById('val-width');
const valLength = document.getElementById('val-length');
const valHeight = document.getElementById('val-height');
const groupLength = document.getElementById('group-length');

// Summary fields
const summaryArea = document.getElementById('summary-area');
const summaryRolls = document.getElementById('summary-rolls');
const summaryPrice = document.getElementById('summary-price');

// Initialize App
async function init() {
    setupTabs();
    setupDimensions();
    setupCalculations();
    setupFurnitureTab();
    setupFloorsTab();
    setupCanvasClick();
    
    // Load products from JSON
    await loadProducts();
}

// Tab Switching
function setupTabs() {
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.getAttribute('data-tab');
            
            tabButtons.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            btn.classList.add('active');
            document.getElementById(`tab-${tabId}`).classList.add('active');
        });
    });
}

// Dimensions handlers
function setupDimensions() {
    // Mode toggle (Whole Room vs Single Wall)
    const modeRadios = document.getElementsByName('calc-mode');
    modeRadios.forEach(radio => {
        radio.addEventListener('change', (e) => {
            calcMode = e.target.value;
            
            // Adjust length slider visibility
            if (calcMode === 'wall') {
                groupLength.style.display = 'none';
            } else {
                groupLength.style.display = 'block';
            }
            
            // Update labels
            document.querySelectorAll('.toggle-label').forEach(label => {
                const isChecked = label.querySelector('input').checked;
                label.style.background = isChecked ? 'var(--accent-light)' : 'rgba(255,255,255,0.05)';
                label.style.borderColor = isChecked ? 'var(--accent)' : 'transparent';
                label.style.color = isChecked ? 'var(--accent)' : 'var(--text-secondary)';
            });
            
            updateDimensionsUI();
            calculateRolls();
        });
    });

    // Inputs
    inputWidth.addEventListener('input', (e) => {
        roomWidth = parseFloat(e.target.value);
        valWidth.textContent = `${roomWidth.toFixed(1)} m`;
        updateDimensionsUI();
        calculateRolls();
    });

    inputLength.addEventListener('input', (e) => {
        roomLength = parseFloat(e.target.value);
        valLength.textContent = `${roomLength.toFixed(1)} m`;
        calculateRolls();
    });

    inputHeight.addEventListener('input', (e) => {
        roomHeight = parseFloat(e.target.value);
        valHeight.textContent = `${roomHeight.toFixed(1)} m`;
        calculateRolls();
    });
    
    // Trigger initial styles
    modeRadios[0].dispatchEvent(new Event('change'));
}

// Change width of the wall in visual representation
function updateDimensionsUI() {
    // We scale the visual room width to match the aspect ratio
    // Eni qancha katta bo'lsa, xonaning 2D nisbiy ko'rinishi eniga biroz o'zgaradi
    const scale = 100 - ((8.0 - roomWidth) * 4); // percentage-based styling
    roomCanvas.style.width = `${Math.min(100, Math.max(70, scale))}%`;
}

// Calculate Wallpaper rolls (matching calculator.py logic)
function calculateRolls() {
    let perimeter = roomWidth;
    if (calcMode === 'room') {
        perimeter = 2 * (roomWidth + roomLength);
    }
    
    const wallArea = perimeter * roomHeight;
    summaryArea.textContent = `${wallArea.toFixed(1)} m²`;

    if (!selectedWallpaper) {
        summaryRolls.textContent = '0 ta';
        summaryPrice.textContent = '0 UZS';
        btnSubmit.disabled = true;
        return;
    }

    // Default standard roll parameters
    const rollWidth = 1.06;
    const rollLength = 10.0;
    const patternRepeat = 0; // standard pattern match

    // Calculate stripes needed
    const stripesNeeded = Math.ceil(perimeter / rollWidth);
    
    // Calculate stripes per roll
    let cutLength = roomHeight;
    if (patternRepeat > 0) {
        cutLength = roomHeight + patternRepeat;
    }
    let stripesPerRoll = Math.floor(rollLength / cutLength);
    if (stripesPerRoll < 1) stripesPerRoll = 1;

    // Total rolls needed
    const rollsNeeded = Math.ceil(stripesNeeded / stripesPerRoll);
    
    // Total price
    const totalPrice = rollsNeeded * selectedWallpaper.priceValue;

    // Update UI
    summaryRolls.textContent = `${rollsNeeded} ta`;
    summaryPrice.textContent = `${totalPrice.toLocaleString().replace(/,/g, ' ')} UZS`;
    btnSubmit.disabled = false;
}

// Load Products from JSON
async function loadProducts() {
    let categories = [];
    try {
        const response = await fetch('../products.json');
        if (!response.ok) throw new Error('Fetch failed');
        categories = await response.json();
    } catch (err) {
        console.warn('Failed to fetch products.json, using fallback data.', err);
        categories = fallbackProducts;
    }
    
    renderWallpapersTab(categories);
}

// Render Wallpapers inside Tab
function renderWallpapersTab(categories) {
    const categoriesDiv = document.getElementById('wallpaper-categories');
    const itemsDiv = document.getElementById('wallpaper-items');
    
    categoriesDiv.innerHTML = '';
    itemsDiv.innerHTML = '';

    // Filter categories that have wallpapers or travertines
    const targetCategories = categories.filter(cat => 
        cat.category.includes('Oboylar') || 
        cat.category.includes('Bo\'yoqlar') ||
        cat.category.includes('Travertin')
    );

    if (targetCategories.length === 0) {
        itemsDiv.innerHTML = `<p style="grid-column: 1/-1; text-align: center; color: var(--text-secondary);">Mahsulotlar topilmadi.</p>`;
        return;
    }

    // Render category buttons
    targetCategories.forEach((cat, idx) => {
        const btn = document.createElement('button');
        btn.className = `cat-btn ${idx === 0 ? 'active' : ''}`;
        btn.textContent = cat.category;
        btn.addEventListener('click', () => {
            document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            renderItems(cat.items);
        });
        categoriesDiv.appendChild(btn);
    });

    // Render items for first category by default
    renderItems(targetCategories[0].items);
    
    function renderItems(items) {
        itemsDiv.innerHTML = '';
        items.forEach(item => {
            const gridItem = document.createElement('div');
            gridItem.className = `grid-item ${selectedWallpaper?.id === item.id ? 'selected' : ''}`;
            
            // Set image or solid preview
            let imgHTML = '';
            if (item.image_file) {
                imgHTML = `<img src="../images/${item.image_file}" class="grid-item-img" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex'">`;
            }
            // CSS preview backup in case image fails to load
            const fallbackStyle = fallbackWallpaperCSS[item.id] || '#cbd5e1';
            const cssPreview = `<div class="grid-item-img fallback-preview" style="display: ${item.image_file ? 'none' : 'flex'}; background: ${fallbackStyle}; align-items:center; justify-content:center; border-radius:4px; font-size:9px; color:#475569; border: 1px solid var(--border-color)">${item.name.substring(0, 3)}</div>`;

            gridItem.innerHTML = `
                ${imgHTML}
                ${cssPreview}
                <span class="grid-item-name">${item.name}</span>
                <span class="grid-item-price">${item.priceValue.toLocaleString()} so'm</span>
            `;

            gridItem.addEventListener('click', () => {
                document.querySelectorAll('#wallpaper-items .grid-item').forEach(el => el.classList.remove('selected'));
                gridItem.classList.add('selected');
                
                selectedWallpaper = item;
                applyWallpaper(item);
                calculateRolls();
            });

            itemsDiv.appendChild(gridItem);
        });
    }
}

// Apply wallpaper texture/image to visual room wall
function applyWallpaper(item) {
    if (item.image_file) {
        // Try setting image background
        const imgUrl = `../images/${item.image_file}`;
        roomWall.style.backgroundImage = `url('${imgUrl}')`;
        roomWall.style.backgroundColor = 'transparent';
        
        // Handle loading error via checking image load
        const img = new Image();
        img.onload = () => {
            roomWall.style.backgroundImage = `url('${imgUrl}')`;
        };
        img.onerror = () => {
            // Apply fallback CSS pattern if image doesn't exist locally
            roomWall.style.backgroundImage = 'none';
            roomWall.style.background = fallbackWallpaperCSS[item.id] || '#f1f5f9';
        };
        img.src = imgUrl;
    } else {
        roomWall.style.backgroundImage = 'none';
        roomWall.style.background = fallbackWallpaperCSS[item.id] || '#f1f5f9';
    }
}

// Render Floors inside Tab
function setupFloorsTab() {
    const floorItemsDiv = document.getElementById('floor-items');
    floorItemsDiv.innerHTML = '';

    Object.keys(floorStyles).forEach(key => {
        const style = floorStyles[key];
        const gridItem = document.createElement('div');
        gridItem.className = `grid-item ${selectedFloor === key ? 'selected' : ''}`;
        
        gridItem.innerHTML = `
            <div class="grid-item-img" style="background: ${style.css}; border-radius: 4px; border: 1px solid var(--border-color)"></div>
            <span class="grid-item-name">${style.name}</span>
        `;

        gridItem.addEventListener('click', () => {
            document.querySelectorAll('#floor-items .grid-item').forEach(el => el.classList.remove('selected'));
            gridItem.classList.add('selected');
            
            selectedFloor = key;
            roomFloor.style.background = style.css;
            if (key === 'carpet') {
                roomFloor.style.backgroundSize = '4px 4px';
            } else if (key === 'tile-gray') {
                roomFloor.style.backgroundSize = '30px auto';
            } else {
                roomFloor.style.backgroundSize = '24px auto';
            }
        });

        floorItemsDiv.appendChild(gridItem);
    });
    
    // Apply initial floor
    roomFloor.style.background = floorStyles[selectedFloor].css;
    roomFloor.style.backgroundSize = '24px auto';
}

// Render Furniture inside Tab
function setupFurnitureTab() {
    const furnitureItemsDiv = document.getElementById('furniture-items');
    furnitureItemsDiv.innerHTML = '';

    furnitureAssets.forEach(asset => {
        const gridItem = document.createElement('div');
        gridItem.className = 'grid-item';
        
        gridItem.innerHTML = `
            <div class="grid-item-img" style="display: flex; align-items: center; justify-content: center; padding: 6px;">
                ${asset.svg}
            </div>
            <span class="grid-item-name">${asset.name}</span>
        `;

        gridItem.addEventListener('click', () => {
            addFurnitureToCanvas(asset);
        });

        furnitureItemsDiv.appendChild(gridItem);
    });
}

// Add placed item to canvas
function addFurnitureToCanvas(asset) {
    const itemId = `placed_${Date.now()}`;
    
    // Calculate standard position
    // We center it horizontally and position it vertically based on its type
    const canvasWidth = roomCanvas.clientWidth;
    const canvasHeight = roomCanvas.clientHeight;
    
    const left = (canvasWidth - asset.width) / 2;
    // vertical positioning: yPos percentage of canvas height
    const top = (canvasHeight * asset.yPos) / 100;

    const newItem = {
        id: itemId,
        type: asset.type,
        name: asset.name,
        width: asset.width,
        height: asset.height,
        left: left,
        top: top,
        scaleX: 1,
        rotate: 0,
        svg: asset.svg
    };

    furnitureItems.push(newItem);
    renderFurnitureItemDOM(newItem);
    selectItem(itemId);
}

// Create DOM element for furniture and attach dragging event handlers
function renderFurnitureItemDOM(item) {
    const el = document.createElement('div');
    el.className = 'furniture-item';
    el.id = item.id;
    el.style.width = `${item.width}px`;
    el.style.height = `${item.height}px`;
    el.style.left = `${item.left}px`;
    el.style.top = `${item.top}px`;
    el.style.transform = `scaleX(${item.scaleX}) rotate(${item.rotate}deg)`;
    
    el.innerHTML = `
        ${item.svg}
        <div class="item-controls">
            <button class="control-btn delete" title="O'chirish">❌</button>
            <button class="control-btn flip" title="Aylantirish">🔄</button>
            <button class="control-btn rotate" title="Burish">↪️</button>
        </div>
    `;

    // Event Handlers for item controls
    el.querySelector('.delete').addEventListener('click', (e) => {
        e.stopPropagation();
        deleteItem(item.id);
    });

    el.querySelector('.flip').addEventListener('click', (e) => {
        e.stopPropagation();
        flipItem(item.id);
    });

    // Touch/Mouse events for dragging the item
    el.addEventListener('mousedown', (e) => startDrag(e, item.id));
    el.addEventListener('touchstart', (e) => startDrag(e, item.id), { passive: false });

    // Custom Rotator handler (drag to rotate)
    const rotateBtn = el.querySelector('.rotate');
    rotateBtn.addEventListener('mousedown', (e) => startRotate(e, item.id));
    rotateBtn.addEventListener('touchstart', (e) => startRotate(e, item.id), { passive: false });

    furnitureLayer.appendChild(el);
}

// Dragging logic
function startDrag(e, itemId) {
    // If clicking on control buttons, ignore dragging
    if (e.target.classList.contains('control-btn')) return;
    
    e.preventDefault();
    selectItem(itemId);
    
    isDragging = true;
    draggedItem = furnitureItems.find(item => item.id === itemId);
    const el = document.getElementById(itemId);
    
    const clientX = e.type.startsWith('touch') ? e.touches[0].clientX : e.clientX;
    const clientY = e.type.startsWith('touch') ? e.touches[0].clientY : e.clientY;
    
    startX = clientX;
    startY = clientY;
    initialLeft = draggedItem.left;
    initialTop = draggedItem.top;
    
    document.addEventListener('mousemove', handleDrag);
    document.addEventListener('touchmove', handleDrag, { passive: false });
    document.addEventListener('mouseup', stopDrag);
    document.addEventListener('touchend', stopDrag);
}

function handleDrag(e) {
    if (!isDragging || !draggedItem) return;
    e.preventDefault();
    
    const clientX = e.type.startsWith('touch') ? e.touches[0].clientX : e.clientX;
    const clientY = e.type.startsWith('touch') ? e.touches[0].clientY : e.clientY;
    
    const dx = clientX - startX;
    const dy = clientY - startY;
    
    let newLeft = initialLeft + dx;
    let newTop = initialTop + dy;
    
    // Bounds limits (keep item inside room canvas)
    const canvasWidth = roomCanvas.clientWidth;
    const canvasHeight = roomCanvas.clientHeight;
    
    newLeft = Math.max(-draggedItem.width/2, Math.min(canvasWidth - draggedItem.width/2, newLeft));
    newTop = Math.max(-draggedItem.height/2, Math.min(canvasHeight - draggedItem.height/2, newTop));
    
    draggedItem.left = newLeft;
    draggedItem.top = newTop;
    
    const el = document.getElementById(draggedItem.id);
    el.style.left = `${newLeft}px`;
    el.style.top = `${newTop}px`;
}

function stopDrag() {
    isDragging = false;
    document.removeEventListener('mousemove', handleDrag);
    document.removeEventListener('touchmove', handleDrag);
    document.removeEventListener('mouseup', stopDrag);
    document.removeEventListener('touchend', stopDrag);
}

// Rotation logic
let isRotating = false;
function startRotate(e, itemId) {
    e.stopPropagation();
    e.preventDefault();
    
    isRotating = true;
    const item = furnitureItems.find(i => i.id === itemId);
    const el = document.getElementById(itemId);
    
    const rect = el.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    
    function handleRotateMove(evt) {
        if (!isRotating) return;
        evt.preventDefault();
        
        const clientX = evt.type.startsWith('touch') ? evt.touches[0].clientX : evt.clientX;
        const clientY = evt.type.startsWith('touch') ? evt.touches[0].clientY : evt.clientY;
        
        // Calculate angle relative to center
        const radians = Math.atan2(clientY - centerY, clientX - centerX);
        let degrees = radians * (180 / Math.PI) - 45; // adjust for handle offset
        if (degrees < 0) degrees += 360;
        
        // Round to nearest 5 degrees for convenience
        degrees = Math.round(degrees / 5) * 5;
        
        item.rotate = degrees;
        el.style.transform = `scaleX(${item.scaleX}) rotate(${degrees}deg)`;
    }
    
    function stopRotate() {
        isRotating = false;
        document.removeEventListener('mousemove', handleRotateMove);
        document.removeEventListener('touchmove', handleRotateMove);
        document.removeEventListener('mouseup', stopRotate);
        document.removeEventListener('touchend', stopRotate);
    }
    
    document.addEventListener('mousemove', handleRotateMove);
    document.addEventListener('touchmove', handleRotateMove, { passive: false });
    document.addEventListener('mouseup', stopRotate);
    document.addEventListener('touchend', stopRotate);
}

// Select/Deselect
function selectItem(itemId) {
    selectedItemId = itemId;
    document.querySelectorAll('.furniture-item').forEach(el => {
        if (el.id === itemId) {
            el.classList.add('selected');
        } else {
            el.classList.remove('selected');
        }
    });
}

function deselectAll() {
    selectedItemId = null;
    document.querySelectorAll('.furniture-item').forEach(el => {
        el.classList.remove('selected');
    });
}

function setupCanvasClick() {
    roomCanvas.addEventListener('click', (e) => {
        // Deselect if clicking on empty area of wall or floor
        if (e.target.id === 'room-wall' || e.target.id === 'room-floor' || e.target.id === 'room-canvas' || e.target.id === 'static-layer' || e.target.id === 'furniture-layer') {
            deselectAll();
        }
    });
}

// Item Actions
function deleteItem(itemId) {
    furnitureItems = furnitureItems.filter(item => item.id !== itemId);
    const el = document.getElementById(itemId);
    if (el) el.remove();
    if (selectedItemId === itemId) selectedItemId = null;
}

function flipItem(itemId) {
    const item = furnitureItems.find(i => i.id === itemId);
    if (item) {
        item.scaleX = item.scaleX === 1 ? -1 : 1;
        const el = document.getElementById(itemId);
        el.style.transform = `scaleX(${item.scaleX}) rotate(${item.rotate}deg)`;
    }
}

// Submission and WebApp Communication
btnSubmit.addEventListener('click', () => {
    if (!selectedWallpaper) return;
    
    // Calculate final results
    let perimeter = roomWidth;
    if (calcMode === 'room') {
        perimeter = 2 * (roomWidth + roomLength);
    }
    
    const rollWidth = 1.06;
    const rollLength = 10.0;
    const patternRepeat = 0;
    const stripesNeeded = Math.ceil(perimeter / rollWidth);
    let cutLength = roomHeight;
    let stripesPerRoll = Math.floor(rollLength / cutLength);
    if (stripesPerRoll < 1) stripesPerRoll = 1;
    const rollsNeeded = Math.ceil(stripesNeeded / stripesPerRoll);
    const totalPrice = rollsNeeded * selectedWallpaper.priceValue;

    // Collect furniture lists for receipt description
    const furnitureSummary = furnitureItems.reduce((acc, item) => {
        acc[item.name] = (acc[item.name] || 0) + 1;
        return acc;
    }, {});
    const furnitureText = Object.keys(furnitureSummary)
        .map(key => `${key} (${furnitureSummary[key]} ta)`)
        .join(', ') || 'Mebel joylashtirilmagan';

    // Prepare data to send back to bot
    const dataToSend = {
        action: 'buy_room',
        room: {
            mode: calcMode === 'room' ? 'Butun xona (4 ta devor)' : 'Faqat 1 ta devor',
            width: roomWidth,
            length: calcMode === 'room' ? roomLength : 0,
            height: roomHeight,
            area: perimeter * roomHeight
        },
        product: {
            id: selectedWallpaper.id,
            name: selectedWallpaper.name,
            price: selectedWallpaper.priceValue,
            rolls: rollsNeeded,
            totalPrice: totalPrice
        },
        furniture: furnitureText,
        floor: floorStyles[selectedFloor].name
    };

    if (tg) {
        // Send data to Telegram Bot
        tg.sendData(JSON.stringify(dataToSend));
        tg.close();
    } else {
        // For local browser testing
        alert("Buyurtma yuborildi!\n\n" + JSON.stringify(dataToSend, null, 2));
    }
});

// Run
window.addEventListener('DOMContentLoaded', init);
