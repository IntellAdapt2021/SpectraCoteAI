// scripts.js
console.log("script.js is loaded and running!");

document.addEventListener('DOMContentLoaded', function () {
    // Your existing JavaScript code here


document.querySelectorAll('.dropdown').forEach((dropdown) => {
    const button = dropdown.querySelector('button');
    const menu = dropdown.querySelector('.dropdown-menu');

    // Show menu on button hover
    button.addEventListener('mouseenter', () => {
        menu.classList.remove('hidden');
    });

    // Keep menu open when hovering over the menu
    menu.addEventListener('mouseenter', () => {
        menu.classList.remove('hidden');
    });

    // Hide menu when leaving the button or menu
    button.addEventListener('mouseleave', () => {
        setTimeout(() => {
            if (!menu.matches(':hover')) {
                menu.classList.add('hidden');
            }
        }, 200);
    });

    menu.addEventListener('mouseleave', () => {
        setTimeout(() => {
            if (!button.matches(':hover')) {
                menu.classList.add('hidden');
            }
        }, 200);
    });
});

// Variables to store original thickness values
let originalFrontThicknesses = [];
let originalBackThicknesses = [];
let updatedFrontThicknesses = [];
let updatedBackThicknesses = [];

// Open the Interactive Simulation modal
document.getElementById('interactiveSimulationButton').addEventListener('click', () => {
    initializeThicknessControls();
    document.getElementById('simulationModal').classList.remove('hidden');
});

// Close the modal
document.getElementById('closeModalButton').addEventListener('click', () => {
    document.getElementById('simulationModal').classList.add('hidden');
});

// Reset changes
document.getElementById('resetChangesButton').addEventListener('click', () => {
    initializeThicknessControls();
    updateGraph(originalFrontThicknesses, originalBackThicknesses);
});

// Apply changes
document.getElementById('applyChangesButton').addEventListener('click', () => {
    // Get the current front and back layer data (materials and thicknesses)
    const frontLayers = getLayerData('frontLayers');
    const backLayers = getLayerData('backLayers');

    // Preserve the original material names
    const preservedFrontMaterials = [...frontLayers.materials];
    const preservedBackMaterials = [...backLayers.materials];

    // Update only the thickness values in the main design
    frontLayers.thicknesses = [...updatedFrontThicknesses];
    backLayers.thicknesses = [...updatedBackThicknesses];

    // Update the UI thickness inputs without altering the material dropdowns
    Array.from(document.querySelectorAll('#frontLayers .thickness-input')).forEach((input, index) => {
        input.value = updatedFrontThicknesses[index];
    });

    Array.from(document.querySelectorAll('#backLayers .thickness-input')).forEach((input, index) => {
        input.value = updatedBackThicknesses[index];
    });

    // Ensure the material dropdown selections remain unchanged
    Array.from(document.querySelectorAll('#frontLayers .material-select')).forEach((select, index) => {
        select.value = preservedFrontMaterials[index];
    });

    Array.from(document.querySelectorAll('#backLayers .material-select')).forEach((select, index) => {
        select.value = preservedBackMaterials[index];
    });

    // Close the modal
    document.getElementById('simulationModal').classList.add('hidden');

    // Notify the user
    alert('Changes have been successfully applied to the design without affecting material selections.');
});

// Event listener for the "Create Stack" button
// Event listener for the Create Stack button
document.getElementById('createStackButton').addEventListener('click', () => {
    const frontLayers = getLayerData('frontLayers');
    const backLayers = getLayerData('backLayers');
    const glassThickness = parseFloat(document.getElementById('dgls').value);

    updateLayerDesign(frontLayers.materials, frontLayers.thicknesses, backLayers.materials, backLayers.thicknesses, glassThickness);
    document.getElementById('stackSection').style.display = 'block'; // Ensure the stack section is visible
});

function openDesign() {
    fetch('/get_user_designs')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Fetched designs:', data); // Log the fetched data
            // Handle the data as needed
        })
        .catch(error => {
            console.error('Error fetching designs:', error);
            alert('Error fetching designs: ' + error.message);
        });
}

function triggerOpenFile() {
    document.getElementById('uploadDesignInput').click();
}

document.getElementById('uploadDesignInput').addEventListener('change', function (event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const design = JSON.parse(e.target.result);
            applyDesign(design);
        };
        reader.readAsText(file);
    }
});

function applyDesign(design) {
    document.getElementById('start_wavelength').value = design.startWavelength;
    document.getElementById('end_wavelength').value = design.endWavelength;
    document.getElementById('theta').value = design.theta;
    document.getElementById('incoh').value = design.incoh;
    document.getElementById('dgls').value = design.glassThickness;

    const frontLayersContainer = document.getElementById('frontLayers');
    frontLayersContainer.innerHTML = '';
    design.frontMaterials.forEach((material, index) => {
        frontLayersContainer.appendChild(createLayerInput(material, design.frontThicknesses[index]));
    });

    const backLayersContainer = document.getElementById('backLayers');
    backLayersContainer.innerHTML = '';
    design.backMaterials.forEach((material, index) => {
        backLayersContainer.appendChild(createLayerInput(material, design.backThicknesses[index]));
    });
}

function loadMaterial() {
    alert("Load Material functionality is currently under construction.");
}

function saveDesign() {
    const designName = document.getElementById('filenameInput').value.trim();
    if (!designName) {
        alert("Please enter a design name.");
        return;
    }

    const visibility = document.querySelector('input[name="visibility"]:checked').value;
    const frontLayers = getLayerData('frontLayers');
    const backLayers = getLayerData('backLayers');
    const glassThickness = parseFloat(document.getElementById('dgls').value);
    const startWavelength = parseFloat(document.getElementById('start_wavelength').value);
    const endWavelength = parseFloat(document.getElementById('end_wavelength').value);

    const designData = {
        name: designName,
        visibility: visibility, // Public or Private
        frontMaterials: frontLayers.materials,
        frontThicknesses: frontLayers.thicknesses,
        backMaterials: backLayers.materials,
        backThicknesses: backLayers.thicknesses,
        glassThickness: glassThickness,
        startWavelength: startWavelength,
        endWavelength: endWavelength,
        theta: parseFloat(document.getElementById('theta').value),
        incoh: parseFloat(document.getElementById('incoh').value),
    };

    fetch('/save_design', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(designData),
    })
        .then((response) => response.json())
        .then((result) => {
            if (result.success) {
                alert("Design saved successfully!");
            } else {
                alert("Error saving design: " + result.error);
            }
        })
        .catch((error) => {
            console.error('Error:', error);
            alert('An error occurred while saving the design.');
        });
}

function downloadGraph() {
    console.log("Downloading Graph as JPEG...");
    Plotly.toImage(document.getElementById('combinedGraph'), { format: 'jpeg', width: 800, height: 600 })
        .then(function(dataUrl) {
            const link = document.createElement('a');
            link.href = dataUrl;
            link.download = 'graph.jpeg';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        })
        .catch(error => {
            console.error('Error downloading graph:', error);
            alert('An error occurred while downloading the graph.');
        });
}

function downloadCSV() {
    console.log("Downloading Data as CSV...");

    if (!result || !result.wavelengths) {
        alert('No data available to download.');
        return;
    }

    let csvContent = 'Wavelength (nm),Transmittance (%),Reflectance (%),Absorptance (%)\n';
    for (let i = 0; i < result.wavelengths.length; i++) {
        // Scale the values by 100 to convert to percentage
        const transmittance = result.transmittance[i] * 100;
        const reflectance = result.reflectance[i] * 100;
        const absorptance = result.absorptance[i] * 100;

        csvContent += `${result.wavelengths[i]},${transmittance},${reflectance},${absorptance}\n`;
    }

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', 'data.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function downloadPDF() {
    console.log("Downloading Data as PDF...");

    if (!result || !result.wavelengths) {
        alert('No data available to download.');
        return;
    }

    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    doc.text('Optical Simulation Data', 14, 10);

    // Prepare table data with values scaled by 100
    const tableData = result.wavelengths.map((wavelength, index) => [
        wavelength,
        (result.transmittance[index] * 100).toFixed(2),
        (result.reflectance[index] * 100).toFixed(2),
        (result.absorptance[index] * 100).toFixed(2),
    ]);

    doc.autoTable({
        head: [['Wavelength (nm)', 'Transmittance (%)', 'Reflectance (%)', 'Absorptance (%)']],
        body: tableData,
    });

    doc.save('data.pdf');
}

function showTransmittance() {
    console.log("Showing Transmittance Graph...");
    document.getElementById('combinedGraph').style.display = 'none';
    document.getElementById('reflectanceGraph').style.display = 'none';

    const transmittance = result.transmittance.map(value => value * 100);

    // Create traces
    const traceT = {
        x: result.wavelengths,
        y: transmittance,
        type: 'scatter',
        mode: 'lines',
        name: 'Transmittance',
        line: { color: 'blue' }
    };

    Plotly.newPlot('transmittanceGraph', [traceT], {
        title: 'Transmittance vs Wavelength',
        xaxis: { title: 'Wavelength (nm)' },
        yaxis: { title: 'Transmittance (%)',
        range: [0,100]
        }
    });

    document.getElementById('transmittanceGraph').style.display = 'block';
}

function getLayerData(containerId) {
    const container = document.getElementById(containerId);
    const materials = Array.from(container.querySelectorAll('.material-select')).map(select => select.value);
    const thicknesses = Array.from(container.querySelectorAll('.thickness-input')).map(input => parseFloat(input.value));
    return { materials, thicknesses };
}

async function loadMaterials(selectElement = null) {
    const response = await fetch('/get_materials');
    const materialsData = await response.json();

    // Prepare options based on materialsData
    const materialSelectOptions = ['<option value="">Select Material</option>'];
    for (const folder in materialsData) {
        materialsData[folder].forEach(material => {
            materialSelectOptions.push(`<option value="${folder}/${material}">${folder} - ${material}</option>`);
        });
    }
    
    // Populate the specified select element or all material-select dropdowns
    if (selectElement) {
        selectElement.innerHTML = materialSelectOptions.join('');
    } else {
        document.querySelectorAll('.material-select').forEach(select => {
            select.innerHTML = materialSelectOptions.join('');
        });
    }
}

async function uploadMaterial() {
    const fileInput = document.getElementById('materialFileInput');
    const file = fileInput.files[0];
    
    if (!file) {
        alert("Please select a file.");
        return;
    }

    // Ensure the file is a CSV
    if (!file.name.toLowerCase().endsWith('.csv')) {
        alert("Please upload a CSV file.");
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        // Send file to server
        const response = await fetch('/upload_material', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            alert("Upload successful!");
            loadMaterials(); // Refresh dropdown options after successful upload
        } else {
            alert(result.error);
        }
    } catch (error) {
        console.error("Upload error:", error);
        alert("An error occurred while uploading the file.");
    }
}

// Event listener to add front and back layers
document.getElementById('addFrontLayer').addEventListener('click', () => {
    document.getElementById('frontLayers').appendChild(createLayerInput());
});

document.getElementById('addBackLayer').addEventListener('click', () => {
    document.getElementById('backLayers').appendChild(createLayerInput());
});

// Load materials on page load
document.addEventListener('DOMContentLoaded', loadMaterials);
});