/**
 * RivalFit — Generador de imágenes IA para carruseles
 * Usa Gemini (NanoBanana usa el mismo modelo internamente)
 *
 * Ejecutar: node generate-images.mjs
 */

import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const IMAGES_DIR = path.join(__dirname, 'images')
const API_KEY = 'AIzaSyCotqBaupPlmW8FcUuXoYdeu8YdG5Uqdv4'

const images = [
  // ─── BÍCEPS ──────────────────────────────────────────────────────
  {
    file: 'biceps-hero.png',
    prompt: 'Professional fitness photography, extremely muscular male arm performing barbell bicep curl, dramatic dark studio lighting with deep red accent light from below, black background, veins visible, peak contraction pose, cinematic quality, photorealistic, no text, no watermark',
  },
  {
    file: 'biceps-anatomy.png',
    prompt: 'Clean anatomical illustration of human arm muscles, bicep brachii highlighted in deep red on dark background, medical diagram style, dark theme, red and white on black, professional infographic style, no text',
  },
  {
    file: 'biceps-curl.png',
    prompt: 'Side view of muscular athlete performing dumbbell curl in dark gym, dramatic side lighting, red rim light, black background, focus on bicep peak contraction, professional sports photography, cinematic, photorealistic',
  },

  // ─── PULL-UPS ─────────────────────────────────────────────────────
  {
    file: 'pullups-hero.png',
    prompt: 'Powerful athlete performing strict pull-ups on metal bar, dark dramatic gym background, red accent lighting from side, back muscles and lats fully contracted, low angle shot looking up, cinematic sports photography, photorealistic, no text',
  },
  {
    file: 'pullups-muscles.png',
    prompt: 'Muscular male back performing pull-up, latissimus dorsi muscles highlighted in red, dark background, anatomical style, dramatic red and black color scheme, professional fitness photography, photorealistic',
  },
  {
    file: 'pullups-technique.png',
    prompt: 'Side profile of athlete at top of pull-up, chin over bar, perfect form, dark gym with moody red lighting, dramatic shadows, cinematic quality, photorealistic, no text',
  },

  // ─── APP PROMO ────────────────────────────────────────────────────
  {
    file: 'app-hero.png',
    prompt: 'Athlete in dark gym holding smartphone showing a dark fitness app with red accents and progress charts, dramatic lighting, cinematic, moody atmosphere, photorealistic, professional lifestyle photography',
  },
  {
    file: 'app-community.png',
    prompt: 'Group of diverse elite athletes in dark modern gym, red accent lighting, sense of community and competition, dramatic composition, cinematic sports photography, photorealistic, no text',
  },
  {
    file: 'app-gym.png',
    prompt: 'Modern CrossFit box interior at night, dark dramatic lighting with red accent lights, barbells and pull-up rigs, professional photography, cinematic, moody and athletic atmosphere, no people, no text',
  },
]

async function generateImage(prompt, filename) {
  const filepath = path.join(IMAGES_DIR, filename)

  if (fs.existsSync(filepath)) {
    console.log(`  ⏭  Ya existe: ${filename}`)
    return true
  }

  // gemini-2.5-flash-image — modelo de generación de imágenes (NanoBanana)
  const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key=${API_KEY}`

  const body = {
    contents: [{ parts: [{ text: prompt }] }],
    generationConfig: {
      responseModalities: ['IMAGE', 'TEXT'],
    },
  }

  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })

    if (!res.ok) {
      const err = await res.text()
      throw new Error(`API error ${res.status}: ${err.slice(0, 300)}`)
    }

    const data = await res.json()
    const part = data?.candidates?.[0]?.content?.parts?.find(p => p.inlineData)

    if (!part?.inlineData?.data) {
      throw new Error(`No image data. Response: ${JSON.stringify(data).slice(0, 300)}`)
    }

    const buffer = Buffer.from(part.inlineData.data, 'base64')
    const ext = part.inlineData.mimeType?.includes('jpeg') ? 'jpg' : 'png'
    const finalPath = filepath.replace('.png', `.${ext}`)
    fs.writeFileSync(finalPath, buffer)
    console.log(`  ✅ Generada: ${path.basename(finalPath)} (${(buffer.length / 1024).toFixed(0)} KB)`)
    return true
  } catch (err) {
    console.error(`  ❌ Error en ${filename}: ${err.message}`)
    return false
  }
}

async function main() {
  console.log('\n🔴 RivalFit — Generador de imágenes IA\n')
  console.log(`📁 Guardando en: ${IMAGES_DIR}\n`)

  if (!fs.existsSync(IMAGES_DIR)) {
    fs.mkdirSync(IMAGES_DIR, { recursive: true })
    console.log('📂 Carpeta images/ creada\n')
  }

  let ok = 0
  let fail = 0

  for (const img of images) {
    process.stdout.write(`Generando ${img.file}... `)
    const success = await generateImage(img.prompt, img.file)
    if (success) ok++
    else fail++
    // Pausa entre requests para no sobrecargar la API
    await new Promise(r => setTimeout(r, 1500))
  }

  console.log(`\n${'─'.repeat(50)}`)
  console.log(`✅ ${ok} imágenes generadas`)
  if (fail > 0) console.log(`❌ ${fail} fallaron`)
  console.log(`\n🚀 Ahora abre los HTML de los carruseles en tu navegador`)
}

main().catch(console.error)
