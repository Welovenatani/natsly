// Three.js helpers for coloring
// This will be extended with actual model loading and coloring logic

// Helper function to load GLTF models
function loadGLTFModel(scene, path, callback) {
    const loader = new THREE.GLTFLoader();
    loader.load(
        path,
        (gltf) => {
            const model = gltf.scene;
            scene.add(model);
            if (callback) callback(model);
        },
        undefined,
        (error) => {
            console.error('Error loading model:', error);
        }
    );
}

// Coloring engine for 3D models
class ColoringEngine3D {
    constructor(model) {
        this.model = model;
        this.originalMaterials = [];
        this.colorHistory = [];
        
        // Store original materials
        this.model.traverse((child) => {
            if (child.isMesh) {
                this.originalMaterials.push({
                    mesh: child,
                    material: child.material
                });
            }
        });
    }
    
    colorRegion(meshIndex, color) {
        if (meshIndex < this.originalMaterials.length) {
            const meshData = this.originalMaterials[meshIndex];
            
            // Save previous color for undo
            this.colorHistory.push({
                mesh: meshData.mesh,
                prevColor: meshData.mesh.material.color.getHex(),
                newColor: color
            });
            
            // Apply new color
            meshData.mesh.material.color.set(color);
        }
    }
    
    undo() {
        if (this.colorHistory.length > 0) {
            const lastAction = this.colorHistory.pop();
            lastAction.mesh.material.color.setHex(lastAction.prevColor);
        }
    }
    
    reset() {
        // Restore original materials
        this.originalMaterials.forEach(item => {
            item.mesh.material = item.material;
        });
        this.colorHistory = [];
    }
}
