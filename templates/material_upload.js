// Object to store custom materials from CSV files
let customMaterials = {};

// Function to handle the CSV file input
function handleMaterialFileInput(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const csvData = e.target.result;
            parseCSVData(csvData);
        };
        reader.readAsText(file);
    }
}

// Parse CSV data and add the material to dropdowns
function parseCSVData(data) {
    const rows = data.split('\n');
    const materialName = prompt("Enter a name for this material:");

    if (!materialName) {
        alert("Material name is required!");
        return;
    }

    const parsedData = {
        wavelength: [],
        n: [],
        k: []
    };

    rows.forEach((row, index) => {
        if (index === 0) return; // Skip the header row
        const [wavelength, n, k] = row.split(',').map(item => parseFloat(item));
        if (!isNaN(wavelength) && !isNaN(n) && !isNaN(k)) {
            parsedData.wavelength.push(wavelength);
            parsedData.n.push(n);
            parsedData.k.push(k);
        }
    });

    // Log custom materials for debugging
    console.log('Custom Materials:', customMaterials);

    customMaterials[materialName] = parsedData;

    // Update the material dropdown UI
    updateMaterialDropdown(materialName);
}

// Update dropdowns with the new material
function updateMaterialDropdown(materialName) {
    const materialSelects = document.querySelectorAll('.material-select'); // Ensure you have this class on your selects
    materialSelects.forEach(select => {
        const option = document.createElement('option');
        option.value = materialName;
        option.textContent = materialName;
        select.appendChild(option);
    });
}

// Initialize file input for material upload
function initializeMaterialLoader(buttonId, fileInputId) {
    document.getElementById(fileInputId).addEventListener('change', handleMaterialFileInput);
}
