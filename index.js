/**
 * WeaveLab Frontend — API Client
 */

let current_job_id = null;
let current_result = null;

let graph = {
    init() {
        this.width = 30;
        this.height = this.width;
        this.radius = this.width / 3;
        this.num_nails = GUI.num_nails.element.value;
        this.max_iter = GUI.num_connections.element.value;

        this.thread_diam = 0.01; // thread width in inches
        this.nail_diam = 0.1;
        this.thread_opacity = 1.0;

        this.svg = d3.select("body").insert("svg", ":first-child")
            .attr("width", "100vw")
            .attr("viewBox", [-this.width / 2, -this.height / 2, this.width, this.height])
        this.svg.append("g");
        this.svg.attr("desc", "Created using WeaveLab");

        // Base frame path
        let frame_path = this.svg.select("g")
            .append("circle")
            .attr("r", this.radius)
            .style("stroke", "#ffbe5700")
            .style("stroke-width", 10)
            .style("fill", "none");

        // Handle zooming and panning
        let zoom = d3.zoom().on('zoom', handleZoom);
        function handleZoom(e) {
            d3.selectAll('svg > g').attr('transform', e.transform);
        }
        d3.select('svg').call(zoom);
    },
    
    get_frame_url() {
        var serializer = new XMLSerializer();
        var source = serializer.serializeToString(this.svg.node());

        if (!source.match(/^<svg[^>]+xmlns="http\:\/\/www\.w3\.org\/2000\/svg"/)) {
            source = source.replace(/^<svg/, '<svg xmlns="http://www.w3.org/2000/svg"');
        }
        if (!source.match(/^<svg[^>]+"http\:\/\/www\.w3\.org\/1999\/xlink"/)) {
            source = source.replace(/^<svg/, '<svg xmlns:xlink="http://www.w3.org/1999/xlink"');
        }
        source = '<?xml version="1.0" standalone="no"?>\r\n' + source;
        return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(source);
    },

    download_frame() {
        var element = document.createElement('a');
        element.setAttribute("href", `${this.get_frame_url()}`);
        element.setAttribute('download', "frame.svg");
        element.style.display = 'none';
        document.body.appendChild(element);
        element.click();
        document.body.removeChild(element);
    },

    download_nail_seq() {
        if (!current_result) return;
        
        let output = `Generated using WeaveLab\n${current_result.total_connections} connections in total\n\n`;
        let steps = current_result.steps;
        
        for (var i = 0; i < steps.length; i++) {
            let step = steps[i];
            if (i === 0 || steps[i - 1].thread_index !== step.thread_index)
                output += `\nThread: [${step.color[0]}, ${step.color[1]}, ${step.color[2]}]\n`;
            
            output += step.to_nail + "\n";
        }
        
        var url = "data:text/plain;charset=utf-8," + encodeURIComponent(output);
        var element = document.createElement('a');
        element.setAttribute("href", `${url}`);
        element.setAttribute('download', "nail_seq.txt");
        element.style.display = 'none';
        document.body.appendChild(element);
        element.click();
        document.body.removeChild(element);
    }
};

/**
 * UI
 */
class UIElement {
    constructor(desc, name, parent, callback, label) {
        this.desc = desc;
        this.name = name;
        this.parent = parent;
        this.callback = callback;
        if (label) {
            this.label = document.createElement("label");
            this.label.for = name;
            this.label.innerHTML = desc;
            parent.appendChild(this.label);
        }
    }
}

class Slider extends UIElement {
    constructor(desc, name, parent, init_val, min, max, callback) {
        super(desc, name, parent, callback, true);
        this.val = init_val;
        this.min = min;
        this.max = max;
        this.disp = document.createElement("p");
        this.disp.innerHTML = this.val;
        parent.appendChild(this.disp);
        this.element = document.createElement("input");
        this.element.id = name;
        this.element.type = "range";
        this.element.classList.add("slider");
        this.element.min = min;
        this.element.max = max;
        this.element.value = this.val;
        this.element.addEventListener("input", (e) => { callback(e); this.disp.innerHTML = e.target.value; });
        parent.appendChild(this.element);
    }
}

class Button extends UIElement {
    constructor(desc, name, parent, callback) {
        super(desc, name, parent, callback, false);
        this.element = document.createElement("button");
        this.element.id = name;
        this.element.innerHTML = `<b> ${this.desc}</b>`;
        this.element.addEventListener("click", callback);
        parent.appendChild(this.element);
    }
}

class TextEntry extends UIElement {
    constructor(desc, name, parent, value, callback) {
        super(desc, name, parent, callback, true);
        this.element = document.createElement("input");
        this.element.type = "text";
        this.element.value = value;
        parent.appendChild(this.element);
    }
}

let download = document.getElementById("download");
let basic_options = document.getElementById("basic");
let advanced_options = document.getElementById("advanced");
let controls = document.getElementById("controls");

let GUI = {
    init() {
        this.nail_seq_download = new Button(
            "Nail sequence",
            "nail_sequence",
            download,
            () => graph.download_nail_seq()
        );
        this.frame_download = new Button(
            "Frame with numbering",
            "frame_download",
            download,
            () => graph.download_frame()
        );
        
        this.regenerate = new Button(
            "Regenerate",
            "regenerate",
            controls,
            () => {
                let fileInput = document.querySelector("input[type='file']");
                if (fileInput.files && fileInput.files[0]) {
                    generate_from_backend(fileInput.files[0]);
                }
            }
        );
        
        this.num_nails = new Slider(
            "Number of nails:",
            "num_nails",
            basic_options,
            300,
            10, 2000,
            (e) => {
                graph.num_nails = e.target.value;
            }
        );
        
        this.num_connections = new Slider(
            "Max # of connections:",
            "num_connections",
            basic_options,
            10000,
            100, 15000,
            (e) => {
                graph.max_iter = e.target.value;
            }
        );

        this.shape_entry = new TextEntry(
            "Frame shape (circle/square/heart/etc):",
            "frame_shape",
            advanced_options,
            "circle",
            (e) => {}
        );
    }
}

GUI.init();

/**
 * BACKEND INTEGRATION
 */

let pollInterval = null;
let animationFrameId = null;
let drawn_step_count = 0;
let is_drawing = false;
let pending_steps = [];

function clear_graph() {
    if (graph.svg) {
        graph.svg.selectAll("*").remove();
        graph.svg.remove();
    }
    if (pollInterval) clearInterval(pollInterval);
    if (animationFrameId) cancelAnimationFrame(animationFrameId);
    drawn_step_count = 0;
    is_drawing = false;
    pending_steps = [];
    current_result = null;
    graph.init();
}

async function generate_from_backend(file) {
    clear_graph();
    
    GUI.regenerate.element.innerHTML = "<b>Uploading...</b>";
    
    let formData = new FormData();
    formData.append("image", file);
    formData.append("params", JSON.stringify({
        num_nails: parseInt(GUI.num_nails.element.value),
        max_connections: parseInt(GUI.num_connections.element.value),
        frame_shape: GUI.shape_entry.element.value || "circle",
        frame_width: graph.width,
        frame_height: graph.height
    }));

    try {
        let response = await fetch("http://localhost:8000/api/generate", {
            method: "POST",
            body: formData
        });
        
        if (!response.ok) {
            let err = await response.json();
            throw new Error(err.detail || "Upload failed");
        }
        
        let data = await response.json();
        current_job_id = data.job_id;
        
        // Start polling much faster for smooth streaming (e.g., 200ms)
        pollInterval = setInterval(poll_job_status, 200);
    } catch (e) {
        console.error(e);
        GUI.regenerate.element.innerHTML = "<b>Error: " + e.message + "</b>";
    }
}

async function poll_job_status() {
    try {
        let response = await fetch(`http://localhost:8000/api/jobs/${current_job_id}`);
        if (!response.ok) {
            clearInterval(pollInterval);
            GUI.regenerate.element.innerHTML = "<b>Job Not Found (Refresh page)</b>";
            console.error("Job not found, server probably restarted.");
            return;
        }
        let data = await response.json();
        
        // Setup nails if this is the first time we see them
        if (data.nail_positions && data.nail_positions.length > 0 && graph.svg.select("g.nail").empty()) {
            setup_nails(data.nail_positions);
        }
        
        // Accumulate new steps
        if (data.steps && data.steps.length > drawn_step_count) {
            let new_steps = data.steps.slice(drawn_step_count);
            drawn_step_count = data.steps.length;
            pending_steps.push(...new_steps);
            
            // Start draining the pending steps if not already doing so
            if (!is_drawing) {
                drain_pending_steps(data.nail_positions);
            }
        }
        
        if (data.status === "running") {
            GUI.regenerate.element.innerHTML = `<b>Generating... ${(data.progress * 100).toFixed(2)}%</b>`;
        } else if (data.status === "completed") {
            clearInterval(pollInterval);
            current_result = data;
            if (pending_steps.length === 0 && !is_drawing) {
                GUI.regenerate.element.innerHTML = "<b>Regenerate</b>";
            }
        } else if (data.status === "failed") {
            clearInterval(pollInterval);
            GUI.regenerate.element.innerHTML = "<b>Failed!</b>";
            console.error("Job failed:", data.error);
        }
    } catch (e) {
        clearInterval(pollInterval);
        console.error("Polling error", e);
        GUI.regenerate.element.innerHTML = "<b>Connection Error</b>";
    }
}

function setup_nails(nail_pos) {
    let nails = graph.svg.select("g")
        .selectAll("g.nail")
        .data(nail_pos)
        .join("g")
        .attr("class", "nail")
        .attr("transform", d => `translate(${d.x}, ${d.y})`);
        
    nails.append("circle")
        .attr("r", graph.nail_diam / 2)
        .attr("fill", "aqua");

    nails.append("text")
        .style("fill", "black")
        .style("stroke-width", `${graph.nail_diam / 100}`)
        .style("stroke", "white")
        .attr("dx", "0")
        .attr("dy", `${(graph.nail_diam / 2) * 0.7}`)
        .attr("font-size", `${graph.nail_diam}px`)
        .attr("text-anchor", "middle")
        .text(d => d.index);
}

function drain_pending_steps(nail_pos) {
    is_drawing = true;
    
    function draw_frame() {
        if (pending_steps.length === 0) {
            is_drawing = false;
            // If backend is complete, update UI
            if (current_result && current_result.status === "completed") {
                GUI.regenerate.element.innerHTML = "<b>Regenerate</b>";
            }
            return;
        }
        
        // Dynamically adjust batch size to drain smoothly over ~10 frames, but always draw at least 1 line
        let batch_size = Math.max(1, Math.ceil(pending_steps.length / 10));
        
        for(let b=0; b < batch_size && pending_steps.length > 0; b++) {
            let step = pending_steps.shift();
            let start = nail_pos[step.from_nail];
            let end = nail_pos[step.to_nail];
            let color = step.color; 
            
            var simpleLine = d3.line();
            graph.svg.select("g")
                .append('path')
                .attr("d", simpleLine([[start.x, start.y], [end.x, end.y]]))
                .attr("class", "string")
                .style("stroke-width", graph.thread_diam)
                .style("stroke", `rgba(${color[0]},${color[1]},${color[2]},${graph.thread_opacity})`)
                .style("fill", "none");
        }
        
        animationFrameId = requestAnimationFrame(draw_frame);
    }
    
    draw_frame();
}

/**
 * IMAGE PREVIEW
 */

const input = document.querySelector("input[type='file']");
const imgPreview = document.getElementById('snapshot');

input.addEventListener("change", function () {
    if (this.files && this.files[0]) {
        let url = URL.createObjectURL(this.files[0]);
        imgPreview.onload = () => URL.revokeObjectURL(url);
        imgPreview.src = url;
        
        // Auto-start generation
        generate_from_backend(this.files[0]);
    }
});

// Hide UI if query param is present
const urlParams = new URLSearchParams(window.location.search);
if (urlParams.get("showUI") === "false") {
    document.getElementById("ui").style.display = "none";
    if (graph.svg) {
        graph.svg.style("width", "100vw").style("left", "0px");
    }
}

// Initial clear setup
clear_graph();