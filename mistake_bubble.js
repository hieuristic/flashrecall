
/**
 * WebGPU Mistake Bubble Visualization
 */

// Shader code
// Common structs
const STRUCTS = `
struct Particle {
  pos : vec2f,
  vel : vec2f,
  radius : f32,
  error : f32, 
  padding1 : f32,
  padding2 : f32,
};

struct Params {
  canvasSize : vec2f,
  dt : f32,
  time : f32,
};
`;

const COMPUTE_SHADER = `
${STRUCTS}

@group(0) @binding(0) var<storage, read_write> particles : array<Particle>;
@group(0) @binding(1) var<uniform> params : Params;

@compute @workgroup_size(64)
fn simulate(@builtin(global_invocation_id) global_id : vec3u) {
  let i = global_id.x;
  if (i >= arrayLength(&particles)) {
    return;
  }

  var p = particles[i];

  // 1. Gravity (pull to center)
  let center = params.canvasSize * 0.5;
  let toCenter = center - p.pos;
  let distToCenter = length(toCenter);
  let dirToCenter = normalize(toCenter);

  // Strength increases with distance (Spring force)
  // k * dist. 
  let k = 2.0; 
  let force = toCenter * k;

  p.vel += force * params.dt;

  // 2. Drag / Damping
  p.vel *= 0.95;

  // 3. Update Position
  p.pos += p.vel * params.dt;

  // 4. Wall Collisions (keep inside canvas)
  let margin = p.radius;
  if (p.pos.x < margin) { p.pos.x = margin; p.vel.x *= -0.8; }
  if (p.pos.x > params.canvasSize.x - margin) { p.pos.x = params.canvasSize.x - margin; p.vel.x *= -0.8; }
  if (p.pos.y < margin) { p.pos.y = margin; p.vel.y *= -0.8; }
  if (p.pos.y > params.canvasSize.y - margin) { p.pos.y = params.canvasSize.y - margin; p.vel.y *= -0.8; }

  // 5. Particle-Particle Collisions
  for (var j = 0u; j < arrayLength(&particles); j++) {
    if (i == j) { continue; }
    let other = particles[j];
    let diff = p.pos - other.pos;
    let dist = length(diff);
    let minDist = p.radius + other.radius + 2.0; // +2 padding

    if (dist < minDist && dist > 0.001) {
      let overlap = minDist - dist;
      let sepDir = diff / dist;
      let response = sepDir * overlap * 0.1; // Soft separation
      p.pos += response;
      p.vel += response * 2.0; 
    }
  }

  particles[i] = p;
}
`;

const RENDER_SHADER = `
${STRUCTS}

@group(0) @binding(0) var<storage, read> particles : array<Particle>;
@group(0) @binding(1) var<uniform> params : Params;

struct VertexOutput {
  @builtin(position) position : vec4f,
  @location(0) uv : vec2f,
  @location(1) color : vec3f,
  @location(2) radius : f32,
};

@vertex
fn vs_main(
  @builtin(vertex_index) vertexIndex : u32,
  @builtin(instance_index) instanceIndex : u32
) -> VertexOutput {
  let p = particles[instanceIndex];

  // Quad vertices (triangle strip order: BL, BR, TL, TR)
  var pos = array<vec2f, 4>(
    vec2f(-1.0, -1.0),
    vec2f( 1.0, -1.0),
    vec2f(-1.0,  1.0),
    vec2f( 1.0,  1.0)
  );

  let vPos = pos[vertexIndex];
  
  // Transform to pixel space
  let worldPos = p.pos + vPos * p.radius;

  // Transform to clip space (-1 to 1)
  // 0 -> -1, width -> 1
  let clipX = (worldPos.x / params.canvasSize.x) * 2.0 - 1.0;
  // 0 -> 1, height -> -1 (flip Y for WebGPU)
  let clipY = (1.0 - (worldPos.y / params.canvasSize.y)) * 2.0 - 1.0; 

  var out : VertexOutput;
  out.position = vec4f(clipX, clipY, 0.0, 1.0);
  out.uv = vPos; // -1 to 1

  // Color interpolation: Green (#1b8a5a) -> Red (#ee3e32)
  let green = vec3f(0.106, 0.541, 0.353); // #1b8a5a
  let red = vec3f(0.933, 0.243, 0.196);   // #ee3e32
  
  // Custom blend (maybe yellow in middle?)
  // Simple mix
  out.color = mix(green, red, p.error);
  out.radius = p.radius;

  return out;
}

@fragment
fn fs_main(in : VertexOutput) -> @location(0) vec4f {
  let dist = length(in.uv);
  if (dist > 1.0) {
    discard;
  }
  
  // Nice soft edge / antialiasing
  let delta = fwidth(dist);
  let alpha = 1.0 - smoothstep(1.0 - delta, 1.0, dist);

  return vec4f(in.color, alpha);
}
`;

export async function initMistakeBubble(canvas, statsContainer, wordsData) {
    if (!navigator.gpu) {
        console.error("WebGPU not supported");
        return;
    }

    const adapter = await navigator.gpu.requestAdapter();
    if (!adapter) {
        console.error("No WebGPU adapter found");
        return;
    }
    const device = await adapter.requestDevice();

    const context = canvas.getContext("webgpu");
    const devicePixelRatio = window.devicePixelRatio || 1;
    const presentationFormat = navigator.gpu.getPreferredCanvasFormat();

    // Resize canvas to display size
    const observer = new ResizeObserver(entries => {
        for (const entry of entries) {
            const width = entry.contentBoxSize[0].inlineSize;
            const height = entry.contentBoxSize[0].blockSize;
            canvas.width = Math.max(1, Math.min(width * devicePixelRatio, device.limits.maxTextureDimension2D));
            canvas.height = Math.max(1, Math.min(height * devicePixelRatio, device.limits.maxTextureDimension2D));
        }
    });
    observer.observe(canvas);

    // Initial size check
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * devicePixelRatio;
    canvas.height = rect.height * devicePixelRatio;

    context.configure({
        device,
        format: presentationFormat,
        alphaMode: "premultiplied",
    });

    // --- Prepare Data ---
    // Ensure we have exactly or up to 15 items.
    const numParticles = wordsData.length;
    // Struct Particle: pos(2), vel(2), radius(1), error(1), pad(2) = 8 floats = 32 bytes
    const particleUnitSize = 32;
    const particleData = new Float32Array(numParticles * 8);

    for (let i = 0; i < numParticles; i++) {
        const w = wordsData[i];
        // Random startup position (Fly in from edges)
        const angle = Math.random() * Math.PI * 2;
        // Start roughly at the edge of the canvas (radius ~ half of max dimension)
        const d = Math.max(canvas.width, canvas.height) * 0.6 + Math.random() * 50;
        const cx = canvas.width / 2;
        const cy = canvas.height / 2;

        particleData[i * 8 + 0] = cx + Math.cos(angle) * d;     // pos.x
        particleData[i * 8 + 1] = cy + Math.sin(angle) * d;    // pos.y
        particleData[i * 8 + 2] = 0;                                // vel.x
        particleData[i * 8 + 3] = 0;                                // vel.y
        // Radius based on error (mistakes). 
        // Assumption: w.error is count of mistakes (higher is bigger)
        // Radius based on error (mistakes). 
        // User requested: 0.2 * tanh(normalized_error)
        const minDimension = Math.min(canvas.width, canvas.height);

        // w.factor is (mistakes / max_mistakes_today) -> 0..1 range
        const tanhFactor = Math.tanh(w.factor || 0);

        let radius = minDimension * 0.2 * tanhFactor;

        // Clamp to avoid being too tiny?
        // Let's ensure a minimal size for visibility (e.g., 10px or based on text)
        // If factor is 0, radius is 0. But we usually filter data > 0 mistakes.
        radius = Math.max(15 * devicePixelRatio, radius);

        particleData[i * 8 + 4] = radius;                           // radius
        particleData[i * 8 + 5] = w.factor;                         // error (color/size factor)
        particleData[i * 8 + 6] = 0; // pad
        particleData[i * 8 + 7] = 0; // pad
    }

    const particleBuffer = device.createBuffer({
        size: particleData.byteLength,
        usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST | GPUBufferUsage.COPY_SRC,
    });
    device.queue.writeBuffer(particleBuffer, 0, particleData);

    // Staging buffer for reading back positions
    const readBuffer = device.createBuffer({
        size: particleData.byteLength,
        usage: GPUBufferUsage.MAP_READ | GPUBufferUsage.COPY_DST,
    });

    // Params Buffer
    const paramBufferSize = 4 * 4; // vec2 size, f32 dt, f32 time
    const paramBuffer = device.createBuffer({
        size: paramBufferSize,
        usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST,
    });

    // --- Pipelines ---
    const computeModule = device.createShaderModule({ code: COMPUTE_SHADER });
    const renderModule = device.createShaderModule({ code: RENDER_SHADER });

    const computePipeline = device.createComputePipeline({
        layout: 'auto',
        compute: { module: computeModule, entryPoint: "simulate" },
    });

    const renderPipeline = device.createRenderPipeline({
        layout: 'auto',
        vertex: { module: renderModule, entryPoint: "vs_main" },
        fragment: {
            module: renderModule,
            entryPoint: "fs_main",
            targets: [{
                format: presentationFormat,
                blend: {
                    color: { srcFactor: 'src-alpha', dstFactor: 'one-minus-src-alpha', operation: 'add' },
                    alpha: { srcFactor: 'one', dstFactor: 'one-minus-src-alpha', operation: 'add' },
                }
            }],
        },
        primitive: {
            topology: "triangle-strip",
        },
    });

    const computeBindGroup = device.createBindGroup({
        layout: computePipeline.getBindGroupLayout(0),
        entries: [
            { binding: 0, resource: { buffer: particleBuffer } },
            { binding: 1, resource: { buffer: paramBuffer } },
        ],
    });

    const renderBindGroup = device.createBindGroup({
        layout: renderPipeline.getBindGroupLayout(0),
        entries: [
            { binding: 0, resource: { buffer: particleBuffer } },
            { binding: 1, resource: { buffer: paramBuffer } },
        ],
    });

    // --- HTML Overlay Setup ---
    // statsContainer should be absolute over the canvas.
    // Ensure we don't override its 'absolute' positioning if set in HTML.
    // If we need to force it, force 'absolute' and top/left 0.
    // But since it's passed in, let's assume HTML handles layout or we ensure it matches canvas.
    // In index.html it is absolute.
    // Removing the 'relative' override which caused it to stack BELOW the canvas.
    statsContainer.style.pointerEvents = 'none';

    // Create word labels
    const labels = [];
    for (let i = 0; i < numParticles; i++) {
        const el = document.createElement('div');
        el.textContent = wordsData[i].text;
        el.style.position = 'absolute';
        el.style.transform = 'translate(-50%, -50%)'; // Center on point
        el.style.pointerEvents = 'none'; // Click through to canvas if needed
        el.style.color = 'white';
        el.style.textShadow = '0px 0px 3px rgba(0,0,0,0.8)'; // Make shadow slightly stronger for readability
        el.style.fontWeight = 'bold';
        el.style.fontSize = '0.75rem'; // Smaller font for smaller bubbles
        el.style.whiteSpace = 'nowrap';
        el.style.textAlign = 'center';
        el.style.display = 'flex';
        el.style.alignItems = 'center';
        el.style.justifyContent = 'center';
        statsContainer.appendChild(el);
        labels.push(el);
    }

    // --- Loop ---
    let lastTime = performance.now();
    let time = 0;

    async function frame() {
        const now = performance.now();
        const dt = Math.min((now - lastTime) / 1000, 0.1); // Cap dt
        lastTime = now;
        time += dt;

        // Update Params
        const paramsData = new Float32Array([
            canvas.width, canvas.height, // size
            dt,
            time
        ]);
        device.queue.writeBuffer(paramBuffer, 0, paramsData);

        const commandEncoder = device.createCommandEncoder();

        // Compute Pass
        const computePass = commandEncoder.beginComputePass();
        computePass.setPipeline(computePipeline);
        computePass.setBindGroup(0, computeBindGroup);
        computePass.dispatchWorkgroups(Math.ceil(numParticles / 64));
        computePass.end();

        // Render Pass
        // Check for dark mode
        const isDark = document.documentElement.classList.contains('dark');
        // Dark: #1a1a1a -> ~0.102, Light: #ffffff -> 1.0
        const clearColor = isDark ? { r: 0.102, g: 0.102, b: 0.102, a: 1 } : { r: 1, g: 1, b: 1, a: 1 };

        const renderPass = commandEncoder.beginRenderPass({
            colorAttachments: [{
                view: context.getCurrentTexture().createView(),
                clearValue: clearColor,
                loadOp: 'clear',
                storeOp: 'store',
            }]
        });
        renderPass.setPipeline(renderPipeline);
        renderPass.setBindGroup(0, renderBindGroup);
        // Draw 4 vertices per instance, numParticles instances
        renderPass.draw(4, numParticles);
        renderPass.end();

        // Readback for HTML Overlay
        commandEncoder.copyBufferToBuffer(particleBuffer, 0, readBuffer, 0, particleData.byteLength);

        device.queue.submit([commandEncoder.finish()]);

        // Async Map for positions
        await readBuffer.mapAsync(GPUMapMode.READ);
        const arrayBuffer = readBuffer.getMappedRange();
        const data = new Float32Array(arrayBuffer);

        // Update DOM
        for (let i = 0; i < numParticles; i++) {
            const x = data[i * 8 + 0] / devicePixelRatio;
            const y = data[i * 8 + 1] / devicePixelRatio;
            const r = data[i * 8 + 4] / devicePixelRatio;

            const label = labels[i];

            // Explicitly match the bubble geometry
            const diameter = r * 2;
            label.style.width = `${diameter}px`;
            label.style.height = `${diameter}px`;
            label.style.left = `${x - r}px`;
            label.style.top = `${y - r}px`;
            // Remove transform centering if we used it before, 
            // but we need to ensure we don't have conflicting transforms.
            // We set it in creation loop, let's reset it here or rely on inline style override if we changed creation.
            // (Note: we should probably remove the transform definition in the creation loop too, 
            // but overriding it here with `transform = 'none'` or just relying on left/top is safer if we change creation).
            // Actually, best to just remove the transform in the creation block. 
            // Since I can't edit that block in this chunk easily without making it huge, 
            // I'll overwrite transform here.
            label.style.transform = 'none';
        }

        readBuffer.unmap();

        requestAnimationFrame(frame);
    }

    requestAnimationFrame(frame);
}
