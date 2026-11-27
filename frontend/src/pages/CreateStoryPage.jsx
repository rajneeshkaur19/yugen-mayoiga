import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { storiesApi, scenesApi, choicesApi, stateApi, endingsApi, aiApi, charactersApi } from '../api/client'
import { useToast } from '../context/ToastContext'

// Curated atmospheric artworks available as visual anchors
const curatedAtmospheres = [
  { id: 'estate', name: 'Mountain Manor (Mayoiga)', image: '/assets/backgrounds/mayoiga-estate-night.png' },
  { id: 'shrine', name: 'Rain-Soaked Torii Gate', image: '/assets/backgrounds/rain-soaked-shrine.png' },
  { id: 'village', name: 'Midnight Machiya Street', image: '/assets/backgrounds/village-street-night.png' },
  { id: 'bamboo', name: 'Whispering Bamboo Grove', image: '/assets/story-covers/cover-bamboo-forest.png' },
  { id: 'engawa', name: 'Moonlit Engawa Corridor', image: '/assets/backgrounds/midnight-engawa.png' },
  { id: 'station', name: 'Silent Railway Platform', image: '/assets/story-covers/cover-silent-station.png' },
]

// Selectable Setting Environments with actual local assets
const settingOptions = [
  {
    id: 'abandoned-house',
    title: 'The Abandoned House',
    kanji: '迷い家',
    locationName: 'The Secluded Estate',
    image: '/assets/story-covers/cover-abandoned-house.png',
    description: 'A quiet mountain manor where lanterns flicker without oil and shoji doors slide shut unprompted.',
  },
  {
    id: 'silent-station',
    title: 'The Silent Station',
    kanji: '無人駅',
    locationName: 'Platform Four',
    image: '/assets/story-covers/cover-silent-station.png',
    description: 'A fog-shrouded rural railway platform where the timetable lists trains from thirty years ago.',
  },
  {
    id: 'mountain-shrine',
    title: 'The Rain-Soaked Shrine',
    kanji: '古社',
    locationName: 'The Flooded Torii Steps',
    image: '/assets/story-covers/cover-shrine-rain.png',
    description: 'Weathered stone steps climbing into ancient cedar woods, guarded by mossy lanterns and cold mountain rain.',
  },
  {
    id: 'forgotten-village',
    title: 'The Lost Village',
    kanji: '隠れ里',
    locationName: 'Cobblestone Crossing',
    image: '/assets/story-covers/cover-lost-village.png',
    description: 'Empty wooden storefronts and narrow alleys where shadows linger long after the dusk lanterns pass.',
  },
  {
    id: 'bamboo-grove',
    title: 'The Bamboo Grove',
    kanji: '竹林',
    locationName: 'The Whispering Path',
    image: '/assets/story-covers/cover-bamboo-forest.png',
    description: 'Towering green bamboo stalks clicking in the midnight wind, hiding stone altars and faded offerings.',
  },
  {
    id: 'midnight-pagoda',
    title: 'The Midnight Pagoda',
    kanji: '五重塔',
    locationName: 'The Cedar Courtyard',
    image: '/assets/story-covers/cover-midnight-letters.png',
    description: 'Crimson cherry petals drifting over weathered tiles under a glowing, watchful winter moon.',
  },
]

// Genre options
const genreOptions = [
  { id: 'Mystery', kanji: '迷', description: 'Hidden truths, locked rooms, and piecing together forgotten fragments.' },
  { id: 'Psychological Thriller', kanji: '怖', description: 'Doubt, paranoia, and characters whose trust is fragile as ice.' },
  { id: 'Dark Fantasy', kanji: '幻', description: 'Ancient folklore, spirits lingering in mist, and supernatural bargains.' },
  { id: 'Horror', kanji: '怪', description: 'Unsettling silence, things moving in shadows, and irreversible dread.' },
  { id: 'Romance', kanji: '愛', description: 'Bittersweet nostalgia, quiet promises, and bonds that defy time.' },
  { id: 'Adventure', kanji: '探', description: 'Venturing into unexplored halls and uncovering the estate’s boundaries.' },
]

// Tone / Atmosphere options
const toneOptions = [
  'Melancholic',
  'Suspenseful',
  'Quiet',
  'Unsettling',
  'Dreamlike',
  'Eerie',
]

// Seasons
const seasonOptions = ['Autumn', 'Winter', 'Spring', 'Summer']

// Story Languages
const languageOptions = [
  { code: 'English', label: 'English', native: 'English' },
  { code: 'Japanese', label: 'Japanese', native: '日本語' },
  { code: 'Hindi', label: 'Hindi', native: 'हिन्दी' },
  { code: 'French', label: 'French', native: 'Français' },
]

// Story Length options
const lengthOptions = [
  { id: 'short', label: 'Short Journey', chapters: '1–2 Chapters', desc: 'A fleeting mystery focused on a single turning point.' },
  { id: 'medium', label: 'Complete Chronicle', chapters: '3–4 Chapters', desc: 'The balanced journey through the estate with multiple branches.' },
  { id: 'long', label: 'Deep Odyssey', chapters: '5+ Chapters', desc: 'An extensive chronicle with dense character secrets and hidden endings.' },
]

export default function CreateStoryPage() {
  const { showToast } = useToast()
  const navigate = useNavigate()

  // Wizard Step (1 to 4)
  const [currentStep, setCurrentStep] = useState(1)

  // Form State
  const [title, setTitle] = useState('')
  const [premise, setPremise] = useState('')
  const [selectedSetting, setSelectedSetting] = useState(settingOptions[0])
  const [customSetting, setCustomSetting] = useState('')
  const [genre, setGenre] = useState('Mystery')
  const [tone, setTone] = useState('Melancholic')
  const [season, setSeason] = useState('Autumn')
  const [storyLanguage, setStoryLanguage] = useState('English')
  const [length, setLength] = useState('medium')

  const [submitting, setSubmitting] = useState(false)

  // Custom Location Modal & Live Generation State
  const [customModalOpen, setCustomModalOpen] = useState(false)
  const [customSettingCreated, setCustomSettingCreated] = useState(null)
  const [customLocForm, setCustomLocForm] = useState({
    name: '',
    atmosphere: 'Eerie and submerged',
    description: '',
    visualDetails: '',
    image: '/assets/backgrounds/mayoiga-estate-night.png',
  })
  const [generatingAi, setGeneratingAi] = useState(false)
  const [aiResponseInfo, setAiResponseInfo] = useState(null)

  async function handleGenerateAiImage() {
    if (!customLocForm.name.trim()) {
      showToast('Please name your custom realm first.', 'error')
      return
    }
    setGeneratingAi(true)
    setAiResponseInfo(null)

    try {
      const res = await aiApi.generateLocationImage({
        name: customLocForm.name.trim(),
        atmosphere: customLocForm.atmosphere.trim() || 'Mysterious and atmospheric',
        description: customLocForm.description.trim() || `An unexplored sanctuary in the mist.`,
        visual_details: customLocForm.visualDetails.trim() || null,
      })

      setAiResponseInfo(res)
      if (res.success && res.image_url) {
        setCustomLocForm((prev) => ({ ...prev, image: res.image_url }))
        showToast('AI environmental image generated successfully.', 'success')
      } else if (res.missing_config) {
        showToast('Provider API key required for live AI generation. Details shown below.', 'error')
      } else {
        showToast(res.message || 'Generation failed.', 'error')
      }
    } catch (err) {
      setAiResponseInfo({
        success: false,
        message: err.message || 'Unable to reach backend AI generation service.',
        missing_config: 'GEMINI_API_KEY or OPENAI_API_KEY in backend/.env',
        prompt_used: `Cinematic concept art of ${customLocForm.name.trim()}. Atmosphere: ${customLocForm.atmosphere.trim()}`,
      })
      showToast(err.message || 'Unable to generate image.', 'error')
    } finally {
      setGeneratingAi(false)
    }
  }

  function handleAcceptCustomLocation() {
    if (!customLocForm.name.trim()) {
      showToast('Please provide a name for your custom realm.', 'error')
      return
    }
    const newCustomSetting = {
      id: 'custom-location',
      title: customLocForm.name.trim(),
      kanji: '創',
      locationName: customLocForm.name.trim(),
      image: customLocForm.image || '/assets/backgrounds/mayoiga-estate-night.png',
      description: customLocForm.description.trim() || `A custom sanctuary wrapped in ${customLocForm.atmosphere || 'a mysterious'} atmosphere.`,
      isCustom: true,
      atmosphere: customLocForm.atmosphere.trim(),
      visualDetails: customLocForm.visualDetails.trim(),
    }
    setCustomSettingCreated(newCustomSetting)
    setSelectedSetting(newCustomSetting)
    setCustomModalOpen(false)
    showToast(`"${newCustomSetting.title}" is now your active story realm.`, 'success')
  }

  // Step navigation validations
  function goToNextStep() {
    if (currentStep === 1) {
      if (!title.trim()) {
        showToast('Please name your chronicle first.', 'error')
        return
      }
    }
    setCurrentStep((prev) => Math.min(4, prev + 1))
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function goToPrevStep() {
    setCurrentStep((prev) => Math.max(1, prev - 1))
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  // Final submission and seed story engine initialization
  async function handleManifestStory() {
    if (!title.trim()) {
      showToast('Give your story a title first.', 'error')
      setCurrentStep(1)
      return
    }

    setSubmitting(true)
    let createdStory = null

    // Determine location name based on selected setting
    const locationName = (selectedSetting.id === 'custom-location' && customSettingCreated?.title)
      ? customSettingCreated.title
      : (customSetting.trim() || selectedSetting.locationName)
    const themeText = (
      premise.trim() ||
      (selectedSetting.id === 'custom-location' && customSettingCreated
        ? `${customSettingCreated.title}. ${customSettingCreated.description}`
        : `${selectedSetting.title}. ${selectedSetting.description}`)
    ).slice(0, 100)

    try {
      // Determine cover image: use AI-generated URL for custom location if available
      const coverImageUrl = (
        selectedSetting.id === 'custom-location' &&
        aiResponseInfo?.success &&
        aiResponseInfo?.image_url &&
        !aiResponseInfo.image_url.startsWith('/assets/')
      ) ? aiResponseInfo.image_url : null

      createdStory = await storiesApi.create({
        title: title.trim(),
        genre,
        theme: themeText,
        tone,
        season,
        length,
        story_language: storyLanguage,
        cover_image_url: coverImageUrl,
      })

      // Generate rich branching narrative graph customized for chosen parameters
      const loc = locationName || 'The Secluded Sanctuary'
      const storyTitle = title.trim()

      const seedScenesData = [
        {
          key: 'start',
          scene_number: 1,
          location: loc,
          mood: `${tone} and atmospheric`.slice(0, 50),
          content: `${season} mist descends heavily over ${loc}. A single lantern flickers beneath the weathered cedar eaves, casting amber warmth onto rain-darkened boards. On a low table rests an unopened envelope sealed with crimson wax, inscribed with your name in delicate calligraphy. Somewhere beyond the garden, a temple bell rings once—its low chime reverberating through the mountain fog. This sanctuary seems to have anticipated your arrival.`,
          haiku: 'Mist gathers the past\nA lantern guards the silence\nFootsteps seek the truth',
          is_ending: false,
        },
        {
          key: 'west_wing',
          scene_number: 2,
          location: 'The Western Corridor',
          mood: 'Uneasy and nostalgic',
          content: 'The wooden floorboards whisper softly beneath your steps. A cracked timetable hangs beside a tarnished mirror, its silvered glass reflecting shadows that linger a second too long. Tucked behind the frame, you discover an old black-and-white photograph of someone whose eyes seem hauntingly familiar. On the reverse, written in still-damp ink: “Some thresholds unlock only when remembered.” A narrow staircase descends toward the cellar, while a papered shoji screen opens toward the hearth chamber.',
          haiku: 'Beneath fading signs\nOld memories stir below\nThe dark holds its breath',
          is_ending: false,
        },
        {
          key: 'hearth_room',
          scene_number: 3,
          location: 'The Hearth Chamber',
          mood: 'Intimate and veiled',
          content: 'Embers pulse with gentle warmth inside the sunken irori hearth. As you unfold the parchment beside the fire, the delicate script recounts a vow made here decades ago—a solemn promise to guard this sanctuary from those who would forget its purpose. A small brass key intricately carved in the shape of a crane slips from the envelope. Behind the sliding screens, an ancient lock mechanism awaits.',
          haiku: 'A letter unfolds\nThe past waits in the shadows\nOne key turns slowly',
          is_ending: false,
        },
        {
          key: 'perimeter_garden',
          scene_number: 4,
          location: 'The Boundary Garden',
          mood: 'Quiet and contemplative',
          content: 'Cold night air carries the scent of pine needles, wet moss, and mountain earth. A stone lantern guides you along a winding gravel path beside a still reflection pond. At an arched bridge, a wooden signpost stands half-buried in fallen leaves. One route leads deeper into the secluded archives, while another climbs toward the moonlit observation veranda.',
          haiku: 'Rain on stone pathways\nWater mirrors quiet skies\nTwo paths wait ahead',
          is_ending: false,
        },
        {
          key: 'cellar_archive',
          scene_number: 5,
          location: 'The Shadowed Archive',
          mood: 'Suspenseful and revelatory',
          content: 'Stone steps descend into a quiet chamber carved directly into mountain bedrock. Shelves of hand-bound chronicles, ancestral lineage scrolls, and sealed lacquer chests line the walls. An open journal on a reading pedestal describes Mayoiga not as a wandering phantom, but as a liminal sanctuary granted to those who carry unresolved vows. A highlighted passage references your exact family crest.',
          haiku: 'Ink on ancient scrolls\nThe lineage of silence\nTruth awakens here',
          is_ending: false,
        },
        {
          key: 'inner_sanctum',
          scene_number: 6,
          location: 'The Inner Sanctum',
          mood: 'Profound and resonant',
          content: 'You step into a grand hall of tatami and polished cedar beams. At the far alcove stands a ceremonial altar surrounded by unlit paper lanterns. Above it hangs a calligraphy scroll reading: “Yūgen—The subtle beauty of mysteries left unsolved.” As your footsteps cross the central threshold, the lanterns begin to glow one by one with a warm, welcoming luminescence. You now hold the power to decide the fate of this sanctuary.',
          haiku: 'Lanterns bloom in dark\nA choice echoes in the hall\nDawn awaits your word',
          is_ending: false,
        },
        {
          key: 'ending_truth',
          scene_number: 7,
          location: 'The Unveiled Dawn',
          mood: 'Serene and transcendent',
          content: `The sliding paper screens glide open to the crisp morning air. Dawn breaks across the mountain ridge, scattering the fog into ribbons of gold. The distant temple bell tolls one final time—a clear, resonant note that settles deep in your chest. The mysteries of ${storyTitle} have not vanished; they have become part of who you are. Stepping past the threshold, you return to the world with a heart at peace.`,
          haiku: 'Dawn touches the eaves\nA quiet truth finds its home\nThe bell tolls no more',
          is_ending: true,
        },
        {
          key: 'ending_eternal',
          scene_number: 8,
          location: 'The Timeless Sanctuary',
          mood: 'Mystical and eternal',
          content: 'The warmth of the irori hearth spreads throughout the ancient estate. Outside, the autumn mist thickens into an impenetrable silver veil, sealing off the noisy world beyond. The letters, the photographs, the quiet corridors—they are no longer remnants of a forgotten past, but companions for the days to come. Mayoiga has found its protector, and you have found your home.',
          haiku: 'Silver mists draw near\nThe hearth burns with steady warmth\nHome is found at last',
          is_ending: true,
        },
        {
          key: 'ending_twilight',
          scene_number: 9,
          location: 'Where the Mists Dissolve',
          mood: 'Melancholic and contemplative',
          content: `You stand at the boundary torii gate as twilight yields to morning grey. Behind you, the lights of ${loc} fade like embers into the mist. You hold the small brass crane key in your palm—tangible proof that this night was real. Some answers remain veiled in shadow, but the journey has indelibly changed you. Your journey ends here, but its echo remains yours.`,
          haiku: 'Footsteps fade away\nA memory in the fog\nThe mountain stays still',
          is_ending: true,
        },
      ]

      // 1. Create all scenes in database and map key -> scene ID
      const sceneIdMap = {}
      for (const sceneData of seedScenesData) {
        const { key, ...payload } = sceneData
        const created = await scenesApi.create(createdStory.id, payload)
        sceneIdMap[key] = created.id
      }

      // 2. Define rich multi-branching choices with meaningful progression
      const choiceLinks = [
        // Scene 1: 3 distinct choices
        {
          from: 'start',
          to: 'west_wing',
          text: 'Follow the distant temple bell deeper toward the western wing.',
          effects: { yugen_meter: 5 },
          order: 0,
        },
        {
          from: 'start',
          to: 'hearth_room',
          text: 'Open the wax-sealed letter beside the glowing embers.',
          effects: { yugen_meter: -5 },
          order: 1,
        },
        {
          from: 'start',
          to: 'perimeter_garden',
          text: 'Step out onto the mossy engawa and scout the misty grounds.',
          effects: { yugen_meter: 10 },
          order: 2,
        },

        // Scene 2 (west_wing): 2 choices
        {
          from: 'west_wing',
          to: 'cellar_archive',
          text: 'Descend the narrow staircase into the shadowed cellar archives.',
          effects: { yugen_meter: 5 },
          order: 0,
        },
        {
          from: 'west_wing',
          to: 'hearth_room',
          text: 'Carry the old photograph toward the warmth of the hearth chamber.',
          effects: { yugen_meter: -5 },
          order: 1,
        },

        // Scene 3 (hearth_room): 2 choices
        {
          from: 'hearth_room',
          to: 'cellar_archive',
          text: 'Search for where the brass crane key was forged in the lower archives.',
          effects: { yugen_meter: 0 },
          order: 0,
        },
        {
          from: 'hearth_room',
          to: 'perimeter_garden',
          text: 'Take a bronze lantern out into the boundary gardens.',
          effects: { yugen_meter: 5 },
          order: 1,
        },

        // Scene 4 (perimeter_garden): 2 choices
        {
          from: 'perimeter_garden',
          to: 'cellar_archive',
          text: 'Inspect the stone foundation and enter the lower archive entrance.',
          effects: { yugen_meter: -5 },
          order: 0,
        },
        {
          from: 'perimeter_garden',
          to: 'inner_sanctum',
          text: 'Cross the arched bridge toward the glowing inner sanctum.',
          effects: { yugen_meter: 10 },
          order: 1,
        },

        // Scene 5 (cellar_archive): 2 choices
        {
          from: 'cellar_archive',
          to: 'inner_sanctum',
          text: 'Ascend into the inner sanctum to confront the core truth of Mayoiga.',
          effects: { hidden_truth_discovered: true, yugen_meter: -15 },
          order: 0,
        },
        {
          from: 'cellar_archive',
          to: 'perimeter_garden',
          text: 'Return to the open air and ponder the weight of the family scrolls.',
          effects: { yugen_meter: 5 },
          order: 1,
        },

        // Scene 6 (inner_sanctum): 3 climax choices leading to genuine endings
        {
          from: 'inner_sanctum',
          to: 'ending_truth',
          text: 'Unseal the sanctuary boundary and return to the waking world with peace.',
          effects: { hidden_unveiled_dawn: true, hidden_truth_discovered: true, yugen_meter: -30 },
          order: 0,
        },
        {
          from: 'inner_sanctum',
          to: 'ending_eternal',
          text: 'Ignite the central keeper flame and accept your stewardship of Mayoiga.',
          effects: { hidden_sanctuary_accepted: true, yugen_meter: 30 },
          order: 1,
        },
        {
          from: 'inner_sanctum',
          to: 'ending_twilight',
          text: 'Leave an offering upon the altar and walk quietly into the dawn mist.',
          effects: { hidden_journey_concluded: true, yugen_meter: 0 },
          order: 2,
        },
      ]

      // 3. Create all choices linking the graph
      for (const link of choiceLinks) {
        await choicesApi.create(createdStory.id, sceneIdMap[link.from], {
          choice_text: link.text,
          effects: link.effects || {},
          condition: null,
          allow_loop: false,
          sort_order: link.order,
          next_scene_id: sceneIdMap[link.to],
        })
      }

      // 4. Register formal story endings
      const endingConfigs = [
        {
          name: 'The Unveiled Dawn',
          conditions: { unveiled_dawn: true },
          seal_text: 'Dawn of Remembrance',
        },
        {
          name: 'The Timeless Sanctuary',
          conditions: { sanctuary_accepted: true },
          seal_text: 'Keeper of the Mist',
        },
        {
          name: 'Where the Mists Dissolve',
          conditions: { journey_concluded: true },
          seal_text: 'Echo in the Fog',
        },
      ]
      for (const endCfg of endingConfigs) {
        try {
          await endingsApi.create(createdStory.id, endCfg)
        } catch {
          // Non-blocking: endings creation is decorative/metadata
        }
      }

      // 5. Seed setting-appropriate story cast if not already present
      try {
        const existingChars = await charactersApi.list(createdStory.id).catch(() => [])
        if (!existingChars || existingChars.length === 0) {
          const settingId = selectedSetting.id
          let settingCharacters = []

          if (settingId === 'mountain-shrine') {
            settingCharacters = [
              {
                name: 'Chiyo',
                role: 'The Shrine Guardian',
                age: 22,
                background: 'A solemn maiden who tends to the rain-soaked torii gate and weathered stone altars.',
                visual_description: 'Rain-dampened vermilion and white shrine robes, braided obsidian hair, holding an unlit bronze ceremonial bell.',
                visual_prompt_anchor: 'Shrine maiden in vermilion hakama, cedar forest background with mossy stone lantern',
                goals: ['Keep the sacred barrier intact', 'Interpret the whispers in the rainfall'],
                fears: ['The bell tolling without hands', 'Forgetting the forgotten deity\'s true name'],
                secrets: ['She left the mountain five years ago but woke up back at the shrine gates with no memory of returning.'],
              },
              {
                name: 'Kaito',
                role: 'The Seeking Pilgrim',
                age: 28,
                background: 'A solitary traveler carrying a soaked bamboo hat and a tarnished heirloom amulet.',
                visual_description: 'Worn indigo traveling coat, mud-flecked straw sandals, carrying a cloth-wrapped wooden staff.',
                visual_prompt_anchor: 'Pilgrim traveler in indigo haori, weathered cedar trees and rain mist',
                goals: ['Find the hidden mountain shrine before sunset', 'Uncover the vow recorded in his family journal'],
                fears: ['Running out of oil before reaching shelter', 'Dying unknown on the mountain trail'],
                secrets: ['The amulet he carries is cold to the touch and hums when thunder echoes.'],
              },
            ]
          } else if (settingId === 'silent-station') {
            settingCharacters = [
              {
                name: 'The Stationmaster',
                role: 'Keeper of Departures',
                age: 64,
                background: 'An elderly attendant who has maintained the deserted platform timetable for over thirty years.',
                visual_description: 'Faded navy Showa-era railway uniform, brass buttons worn smooth, holding a pocket watch with stopped hands.',
                visual_prompt_anchor: 'Elderly railway attendant in vintage uniform, fog-covered train platform with vintage lantern',
                goals: ['Announce every scheduled arrival faithfully', 'Ensure no passenger steps onto the phantom tracks'],
                fears: ['The final train stopping and nobody boarding', 'Hearing footsteps from the abandoned tunnel'],
                secrets: ['He no longer remembers which station this was before the mountain claimed the line.'],
              },
              {
                name: 'Minato',
                role: 'The Delayed Traveler',
                age: 19,
                background: 'A quiet youth sitting on a weathered wooden bench, clutching an undated return ticket.',
                visual_description: 'Dark wool school coat, frayed scarf against the winter chill, watchful amber eyes.',
                visual_prompt_anchor: 'Young passenger in dark coat, steam and fog on desolate wooden platform bench',
                goals: ['Catch the train to the southern terminal', 'Deliver an unread letter to someone who may no longer exist'],
                fears: ['Looking down at the ticket and finding the ink faded', 'The station lanterns extinguishing simultaneously'],
                secrets: ['The date printed on his ticket matches the night thirty years ago when the railway ceased operations.'],
              },
            ]
          } else if (settingId === 'forgotten-village') {
            settingCharacters = [
              {
                name: 'Sachi',
                role: 'The Village Weaver',
                age: 24,
                background: 'An artisan weaving silent cloth at a midnight wooden loom beneath empty eaves.',
                visual_description: 'Deep navy kasuri kimono, hair pinned with polished boxwood, hands dyed with faint indigo stains.',
                visual_prompt_anchor: 'Japanese weaver in traditional kasuri kimono, dark wooden machiya interior with thread spools',
                goals: ['Finish the ceremonial shroud before the mountain fog rises', 'Keep the loom shuttle moving rhythmic and steady'],
                fears: ['A thread snapping during the third chime', 'Seeing an unfamiliar face in the garden reflection pond'],
                secrets: ['The silk she weaves is spun from spiderwebs gathered from Mayoiga’s forbidden attic.'],
              },
              {
                name: 'Jin',
                role: 'The Night Watchman',
                age: 38,
                background: 'Patrols the dark alleyways and cobblestones, striking two wooden clappers to mark the hours.',
                visual_description: 'Heavy padded winter coat, straw rain cape, carrying a paper lantern that casts bird-shaped silhouettes.',
                visual_prompt_anchor: 'Village watchman in straw cape holding amber paper lantern, misty cobblestone alley',
                goals: ['Ensure every shoji door remains bolted until dawn', 'Track any footprints that do not belong to the living'],
                fears: ['An echo answering his clappers from behind him', 'Finding a lantern lit in an abandoned house'],
                secrets: ['He has not seen a sunrise in three years, yet he never grows tired.'],
              },
            ]
          } else if (settingId === 'bamboo-grove') {
            settingCharacters = [
              {
                name: 'Takeo',
                role: 'The Forest Hermit',
                age: 52,
                background: 'A stoic carver who lives among towering bamboo stalks, whittling protective talismans.',
                visual_description: 'Simple linen work tunic, weathered calloused hands, small carving chisel tucked into his sash.',
                visual_prompt_anchor: 'Hermit woodcarver in linen tunic, green bamboo forest filtered with ethereal sunbeams',
                goals: ['Carve seven talismans before the wind shifts', 'Protect the boundary stones from being overturned'],
                fears: ['The bamboo stalks whispering in human voices', 'Waking up to find his talismans split in two'],
                secrets: ['Each charm he carves holds the name of a traveler who entered the grove and never returned.'],
              },
              {
                name: 'Shiori',
                role: 'The Masked Maiden',
                age: 20,
                background: 'A graceful spirit-like figure wearing an antique porcelain kitsune mask.',
                visual_description: 'White and pale green silk kimono patterned with autumn bamboo leaves, porcelain fox mask tilted to the side.',
                visual_prompt_anchor: 'Mysterious maiden with antique kitsune mask, ethereal moonlit bamboo grove',
                goals: ['Guide lost souls away from the cliff edge', 'Find the companion who gave her the porcelain mask'],
                fears: ['Removing the mask and having no face beneath', 'The sound of dogs barking in the distance'],
                secrets: ['She cannot speak her own name unless someone asks her in the middle of a thunderstorm.'],
              },
            ]
          } else {
            // Default: Mayoiga Manor / Custom Location
            settingCharacters = [
              {
                name: 'Ren',
                role: 'The Quiet Caretaker',
                age: 25,
                background: `The silent steward of ${loc}, attending to paper lanterns and cedar corridors without asking for gratitude.`,
                visual_description: 'Dark grey formal haori over simple black kimono, tidy topknot, ink-stained fingertips, amber eyes.',
                visual_prompt_anchor: 'Solemn youth in dark haori holding brass lantern, traditional Japanese tatami hallway background',
                goals: ['Keep the hearth fire burning throughout the night', 'Ensure guests feel welcome without knowing why'],
                fears: ['The oil in the irori running completely dry', 'A visitor attempting to break the sealed attic latch'],
                secrets: ['He is bound to the estate by a promise made long before the current era.'],
              },
              {
                name: 'Aoi',
                role: 'The Wandering Archivist',
                age: 23,
                background: `An inquisitive chronicler who arrived at ${loc} years ago carrying missing lineage records.`,
                visual_description: 'Layered indigo and cream kimono, spectacles resting on a silk cord, holding a leather-bound chronicle.',
                visual_prompt_anchor: 'Studious archivist with spectacles and indigo kimono, paper scroll archive background',
                goals: ['Complete the genealogy of Mayoiga\'s visitors', 'Discover the fate of the last family who lived here'],
                fears: ['Ink fading from the scrolls overnight', 'Discovering her own name written in the book of the deceased'],
                secrets: ['She suspects the protagonist was chosen by the estate long before this night began.'],
              },
            ]
          }

          for (const charData of settingCharacters) {
            try {
              await charactersApi.create(createdStory.id, charData)
            } catch {
              // Non-blocking
            }
          }
        }
      } catch {
        // Non-blocking: character seeding shouldn't block story manifestation
      }

      await stateApi.get(createdStory.id)
      showToast('Your chronicle has manifested. Entering the sanctuary...', 'success')
      navigate(`/stories/${createdStory.id}`, { replace: true })
    } catch (error) {
      if (createdStory?.id) {
        await storiesApi.delete(createdStory.id).catch(() => {})
      }
      showToast(
        createdStory
          ? `Initial story setup failed (${error.message}). Partial record was rolled back so you can try again.`
          : error.message || 'Unable to create your story.',
        'error'
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#101317] text-[#F1EEE8] font-sans selection:bg-[#A33B42] selection:text-white">
      {/* ─────────────────────────────────────────────────────────────
          1. HEADER WITH MINIMAL NAVIGATION & PROGRESS INDICATOR
      ───────────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-40 border-b border-white/[0.08] bg-[#101317]/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <Link
            to="/dashboard"
            className="group flex items-center gap-2.5 text-xs text-[#858A8D] hover:text-[#C4AD88] transition"
          >
            <span className="flex h-7 w-7 items-center justify-center rounded border border-white/10 bg-[#1B2228] text-sm group-hover:border-[#C4AD88] transition">
              ←
            </span>
            <span className="hidden sm:inline font-medium">Sanctuary Library</span>
          </Link>

          {/* Center Brand Title */}
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded border border-[#C4AD88]/30 bg-[#1B2228] text-[#C4AD88]">
              <svg className="h-4 w-4 text-[#A33B42]" viewBox="0 0 24 24" fill="currentColor">
                <path d="M2 5h20v2H2V5zm3 3h14v2H5V8zm2 3h2v11H7V11zm8 0h2v11h-2V11zM1 3h22v2H1V3z" />
              </svg>
            </div>
            <span className="font-cinematic text-lg font-bold tracking-widest text-[#F1EEE8]">
              MANIFEST CHRONICLE
            </span>
          </div>

          <span className="text-[11px] font-mono text-[#C4AD88]">
            Step 0{currentStep} of 04
          </span>
        </div>

        {/* Step Progress Line */}
        <div className="h-0.5 w-full bg-white/5">
          <div
            className="h-full bg-gradient-to-r from-[#A33B42] to-[#C4AD88] transition-all duration-500"
            style={{ width: `${(currentStep / 4) * 100}%` }}
          />
        </div>
      </header>

      {/* ─────────────────────────────────────────────────────────────
          2. HERO BANNER (COMPACT & CINEMATIC)
      ───────────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden border-b border-white/[0.08] py-8 sm:py-12 px-6 text-center">
        <div
          className="absolute inset-0 bg-cover bg-center bg-no-repeat opacity-35 filter brightness-95 contrast-125 transition-all duration-700"
          style={{ backgroundImage: `url('${selectedSetting.image}')` }}
        />
        <div className="absolute inset-0 bg-gradient-to-b from-[#101317]/70 via-[#101317]/90 to-[#101317]" />

        <div className="relative z-10 mx-auto max-w-2xl">
          <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-[#C4AD88]/30 bg-[#1B2228]/80 px-3 py-0.5 text-[11px] font-mono text-[#C4AD88]">
            <span>幽玄 · 世界創世</span>
            <span>· World Weaver</span>
          </div>
          <h1 className="font-cinematic text-3xl sm:text-5xl font-semibold tracking-wide text-[#F1EEE8]">
            Begin a Story That Remembers.
          </h1>
          <p className="mt-2.5 font-cinematic text-base sm:text-lg italic text-[#D7DCE0]">
            “Choose a world. Define its silence. Decide what it remembers.”
          </p>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────
          3. MAIN STEP WIZARD CONTAINER
      ───────────────────────────────────────────────────────────── */}
      <main className="mx-auto max-w-4xl px-6 py-10 pb-28">
        {/* Step Tabs Indicator */}
        <div className="mb-10 flex items-center justify-between border-b border-white/[0.08] pb-4 overflow-x-auto text-xs">
          {[
            { num: 1, title: 'The World' },
            { num: 2, title: 'The Nature' },
            { num: 3, title: 'The Experience' },
            { num: 4, title: 'Manifestation' },
          ].map((s) => (
            <button
              key={s.num}
              onClick={() => s.num < currentStep && setCurrentStep(s.num)}
              className={`flex items-center gap-2 transition ${
                currentStep === s.num
                  ? 'text-[#C4AD88] font-semibold'
                  : s.num < currentStep
                  ? 'text-[#858A8D] hover:text-[#D7DCE0]'
                  : 'text-white/20 cursor-not-allowed'
              }`}
            >
              <span
                className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-mono ${
                  currentStep === s.num
                    ? 'bg-[#C4AD88] text-[#101317]'
                    : s.num < currentStep
                    ? 'bg-white/10 text-[#C4AD88]'
                    : 'bg-white/5 text-[#858A8D]'
                }`}
              >
                {s.num}
              </span>
              <span className="whitespace-nowrap">{s.title}</span>
            </button>
          ))}
        </div>

        {/* ─────────────────────────────────────────────────────────
            STEP 1: THE WORLD (Title, Premise, Selectable Environments)
        ───────────────────────────────────────────────────────── */}
        {currentStep === 1 && (
          <div className="space-y-8 animate-fadeIn">
            <div>
              <span className="text-[10px] uppercase font-mono tracking-widest text-[#C4AD88]">Phase 01</span>
              <h2 className="font-cinematic text-3xl font-semibold text-[#F1EEE8] mt-1">
                Name Your World & Choose Its Threshold
              </h2>
              <p className="text-xs text-[#858A8D] mt-1">
                Every story in Mayoiga begins with a name and a threshold where memory lingers.
              </p>
            </div>

            {/* Title & Premise Inputs */}
            <div className="space-y-5 rounded-2xl border border-white/10 bg-[#171C21] p-6 sm:p-8">
              <div>
                <label htmlFor="title" className="block text-xs uppercase tracking-wider text-[#C4AD88] font-mono mb-2">
                  Chronicle Title <span className="text-[#A33B42]">*</span>
                </label>
                <input
                  id="title"
                  type="text"
                  required
                  maxLength={200}
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. The Night the Bell Fell Silent"
                  className="w-full rounded-xl border border-white/10 bg-[#101317] px-4 py-3.5 text-base sm:text-lg font-cinematic text-[#F1EEE8] placeholder-[#858A8D] outline-none focus:border-[#C4AD88]/60 transition"
                />
              </div>

              <div>
                <label htmlFor="premise" className="block text-xs uppercase tracking-wider text-[#858A8D] font-mono mb-2">
                  Premise or Central Mystery (Optional)
                </label>
                <textarea
                  id="premise"
                  rows={2}
                  maxLength={100}
                  value={premise}
                  onChange={(e) => setPremise(e.target.value)}
                  placeholder="e.g. A vow forgotten twenty years ago surfaces when the rain begins..."
                  className="w-full rounded-xl border border-white/10 bg-[#101317] px-4 py-3 text-xs sm:text-sm text-[#F1EEE8] placeholder-[#858A8D] outline-none focus:border-[#C4AD88]/60 transition resize-none"
                />
                <span className="text-[10px] text-[#858A8D] font-mono text-right block mt-1">
                  {premise.length}/100 characters
                </span>
              </div>
            </div>

            {/* Selectable Setting Cards with ACTUAL images */}
            <div>
              <label className="block text-xs uppercase tracking-wider text-[#C4AD88] font-mono mb-4">
                Choose Environmental Setting
              </label>

              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {settingOptions.map((set) => {
                  const isSelected = selectedSetting.id === set.id
                  return (
                    <button
                      key={set.id}
                      type="button"
                      onClick={() => setSelectedSetting(set)}
                      className={`group relative flex flex-col justify-between overflow-hidden rounded-xl border text-left transition-all ${
                        isSelected
                          ? 'border-[#C4AD88] bg-[#1B2228] shadow-[0_0_20px_rgba(196,173,136,0.3)] ring-1 ring-[#C4AD88]'
                          : 'border-white/10 bg-[#171C21] hover:border-white/20'
                      }`}
                    >
                      {/* Image Header */}
                      <div className="relative h-32 w-full overflow-hidden bg-[#101317]">
                        <img
                          src={set.image}
                          alt={set.title}
                          className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
                        />
                        <div className="absolute inset-0 bg-gradient-to-t from-[#171C21] via-transparent to-black/30" />
                        <span className="absolute top-2.5 right-2.5 rounded bg-black/60 px-2 py-0.5 font-cinematic text-xs text-[#C4AD88] backdrop-blur-sm">
                          {set.kanji}
                        </span>
                      </div>

                      {/* Card Content */}
                      <div className="p-4 flex-1 flex flex-col justify-between">
                        <div>
                          <h4 className="font-cinematic text-lg font-semibold text-[#F1EEE8] group-hover:text-[#C4AD88] transition">
                            {set.title}
                          </h4>
                          <p className="mt-1 text-[11px] text-[#858A8D] line-clamp-2 leading-relaxed">
                            {set.description}
                          </p>
                        </div>

                        <div className="mt-3 pt-2.5 border-t border-white/5 flex items-center justify-between text-[10px] font-mono">
                          <span className="text-[#C4AD88]">{set.locationName}</span>
                          {isSelected && <span className="text-[#A33B42] font-semibold">Selected ✓</span>}
                        </div>
                      </div>
                    </button>
                  )
                })}

                {/* 7th Card: Other / Custom Location */}
                <div
                  className={`group relative flex flex-col justify-between overflow-hidden rounded-xl border text-left transition-all ${
                    selectedSetting.id === 'custom-location'
                      ? 'border-[#C4AD88] bg-[#1B2228] shadow-[0_0_20px_rgba(196,173,136,0.3)] ring-1 ring-[#C4AD88]'
                      : 'border-white/10 bg-[#171C21] hover:border-white/20'
                  }`}
                >
                  {customSettingCreated ? (
                    <>
                      <div
                        onClick={() => setSelectedSetting(customSettingCreated)}
                        className="cursor-pointer relative h-32 w-full overflow-hidden bg-[#101317]"
                      >
                        <img
                          src={customSettingCreated.image}
                          alt={customSettingCreated.title}
                          className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
                        />
                        <div className="absolute inset-0 bg-gradient-to-t from-[#171C21] via-transparent to-black/30" />
                        <span className="absolute top-2.5 right-2.5 rounded bg-black/60 px-2 py-0.5 font-cinematic text-xs text-[#C4AD88] backdrop-blur-sm">
                          創 · Custom
                        </span>
                      </div>

                      <div className="p-4 flex-1 flex flex-col justify-between">
                        <div
                          onClick={() => setSelectedSetting(customSettingCreated)}
                          className="cursor-pointer"
                        >
                          <div className="flex items-center justify-between">
                            <h4 className="font-cinematic text-lg font-semibold text-[#F1EEE8] group-hover:text-[#C4AD88] transition">
                              {customSettingCreated.title}
                            </h4>
                            <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-[#A33B42]/20 text-[#C4AD88] border border-[#A33B42]/30">
                              Original
                            </span>
                          </div>
                          <p className="mt-1 text-[11px] text-[#858A8D] line-clamp-2 leading-relaxed">
                            {customSettingCreated.description}
                          </p>
                        </div>

                        <div className="mt-3 pt-2.5 border-t border-white/5 flex items-center justify-between text-[10px] font-mono">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation()
                              setCustomModalOpen(true)
                            }}
                            className="text-[#C4AD88] hover:text-white underline transition"
                          >
                            ✎ Edit / Regenerate
                          </button>
                          {selectedSetting.id === 'custom-location' && (
                            <span className="text-[#A33B42] font-semibold">Selected ✓</span>
                          )}
                        </div>
                      </div>
                    </>
                  ) : (
                    <div
                      onClick={() => setCustomModalOpen(true)}
                      className="flex-1 flex flex-col justify-between p-5 cursor-pointer hover:bg-white/[0.02] transition"
                    >
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-dashed border-[#C4AD88]/50 bg-[#101317] text-[#C4AD88] group-hover:scale-105 transition-transform">
                          <span className="font-cinematic text-lg">創</span>
                        </div>
                        <span className="text-[10px] font-mono text-[#C4AD88] border border-[#C4AD88]/30 px-2 py-0.5 rounded bg-[#101317]">
                          + Custom Realm
                        </span>
                      </div>

                      <div className="my-auto py-2">
                        <h4 className="font-cinematic text-lg font-semibold text-[#F1EEE8] group-hover:text-[#C4AD88] transition">
                          Other / Custom Location
                        </h4>
                        <p className="mt-1.5 text-[11px] text-[#858A8D] leading-relaxed">
                          Forge an original threshold. Define custom lore, atmosphere, and generate or select environmental imagery.
                        </p>
                      </div>

                      <div className="mt-4 pt-3 border-t border-dashed border-white/10 flex items-center justify-between">
                        <span className="text-[11px] font-mono text-[#C4AD88] group-hover:underline flex items-center gap-1">
                          <span>+ Forge New Realm</span>
                          <span>→</span>
                        </span>
                        <span className="text-[10px] text-[#858A8D] font-mono">AI Generated</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ─────────────────────────────────────────────────────────
            STEP 2: THE NATURE OF THE STORY (Genre, Tone, Season)
        ───────────────────────────────────────────────────────── */}
        {currentStep === 2 && (
          <div className="space-y-8 animate-fadeIn">
            <div>
              <span className="text-[10px] uppercase font-mono tracking-widest text-[#C4AD88]">Phase 02</span>
              <h2 className="font-cinematic text-3xl font-semibold text-[#F1EEE8] mt-1">
                Define the Story's Soul & Atmosphere
              </h2>
              <p className="text-xs text-[#858A8D] mt-1">
                Select the emotional frequency and seasonal atmosphere that will guide character reactions.
              </p>
            </div>

            {/* Genre Grid */}
            <div>
              <label className="block text-xs uppercase tracking-wider text-[#C4AD88] font-mono mb-3">
                Genre Frequency
              </label>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {genreOptions.map((g) => {
                  const isSelected = genre === g.id
                  return (
                    <button
                      key={g.id}
                      type="button"
                      onClick={() => setGenre(g.id)}
                      className={`rounded-xl border p-4 text-left transition ${
                        isSelected
                          ? 'border-[#A33B42] bg-[#1B2228] shadow-[0_0_20px_rgba(163,59,66,0.3)] ring-1 ring-[#A33B42]'
                          : 'border-white/10 bg-[#171C21] hover:border-white/20'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-cinematic text-lg font-semibold text-[#F1EEE8]">{g.id}</span>
                        <span className="font-cinematic text-sm text-[#C4AD88]">{g.kanji}</span>
                      </div>
                      <p className="mt-1 text-[11px] text-[#858A8D] leading-relaxed">
                        {g.description}
                      </p>
                    </button>
                  )
                })}

              </div>
            </div>

            {/* Tone & Season Selections */}
            <div className="grid gap-6 sm:grid-cols-2 rounded-2xl border border-white/10 bg-[#171C21] p-6 sm:p-8">
              {/* Tone Selection */}
              <div>
                <label className="block text-xs uppercase tracking-wider text-[#C4AD88] font-mono mb-3">
                  Dominant Atmosphere (Tone)
                </label>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  {toneOptions.map((t) => (
                    <button
                      key={t}
                      type="button"
                      onClick={() => setTone(t)}
                      className={`rounded-lg border px-3 py-2 text-left transition ${
                        tone === t
                          ? 'border-[#C4AD88] bg-[#C4AD88]/15 text-[#C4AD88] font-medium'
                          : 'border-white/5 bg-[#101317] text-[#858A8D] hover:text-[#D7DCE0]'
                      }`}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>

              {/* Season Selection */}
              <div>
                <label className="block text-xs uppercase tracking-wider text-[#C4AD88] font-mono mb-3">
                  Season of the Estate
                </label>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  {seasonOptions.map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => setSeason(s)}
                      className={`rounded-lg border px-3 py-2 text-left transition ${
                        season === s
                          ? 'border-[#A33B42] bg-[#A33B42]/20 text-[#F1EEE8] font-medium'
                          : 'border-white/5 bg-[#101317] text-[#858A8D] hover:text-[#D7DCE0]'
                      }`}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ─────────────────────────────────────────────────────────
            STEP 3: THE EXPERIENCE (Story Language & Story Length)
        ───────────────────────────────────────────────────────── */}
        {currentStep === 3 && (
          <div className="space-y-8 animate-fadeIn">
            <div>
              <span className="text-[10px] uppercase font-mono tracking-widest text-[#C4AD88]">Phase 03</span>
              <h2 className="font-cinematic text-3xl font-semibold text-[#F1EEE8] mt-1">
                Configure Story Length & Script Language
              </h2>
              <p className="text-xs text-[#858A8D] mt-1">
                Story language governs narrative generation, kept distinct from your interface language.
              </p>
            </div>

            {/* Story Language Selection */}
            <div className="rounded-2xl border border-white/10 bg-[#171C21] p-6 sm:p-8 space-y-4">
              <label className="block text-xs uppercase tracking-wider text-[#C4AD88] font-mono">
                Story Language
              </label>
              <div className="grid gap-3 sm:grid-cols-4">
                {languageOptions.map((l) => {
                  const isSelected = storyLanguage === l.code
                  return (
                    <button
                      key={l.code}
                      type="button"
                      onClick={() => setStoryLanguage(l.code)}
                      className={`rounded-xl border p-4 text-left transition ${
                        isSelected
                          ? 'border-[#C4AD88] bg-[#1B2228] shadow-[0_0_15px_rgba(196,173,136,0.3)] ring-1 ring-[#C4AD88]'
                          : 'border-white/5 bg-[#101317] text-[#858A8D] hover:text-[#D7DCE0]'
                      }`}
                    >
                      <span className="text-sm font-semibold text-[#F1EEE8] block">{l.label}</span>
                      <span className="text-xs font-mono text-[#C4AD88] block mt-0.5">{l.native}</span>
                    </button>
                  )
                })}

              </div>
            </div>

            {/* Story Length Selection */}
            <div className="space-y-4">
              <label className="block text-xs uppercase tracking-wider text-[#C4AD88] font-mono">
                Manuscript Scope & Length
              </label>
              <div className="grid gap-4 sm:grid-cols-3">
                {lengthOptions.map((len) => {
                  const isSelected = length === len.id
                  return (
                    <button
                      key={len.id}
                      type="button"
                      onClick={() => setLength(len.id)}
                      className={`rounded-2xl border p-5 text-left transition ${
                        isSelected
                          ? 'border-[#A33B42] bg-[#1B2228] shadow-[0_0_20px_rgba(163,59,66,0.3)] ring-1 ring-[#A33B42]'
                          : 'border-white/10 bg-[#171C21] hover:border-white/20'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-cinematic text-xl font-semibold text-[#F1EEE8]">{len.label}</span>
                        <span className="rounded bg-white/5 px-2 py-0.5 text-[10px] font-mono text-[#C4AD88]">
                          {len.chapters}
                        </span>
                      </div>
                      <p className="mt-2 text-xs text-[#858A8D] leading-relaxed">
                        {len.desc}
                      </p>
                    </button>
                  )
                })}

              </div>
            </div>
          </div>
        )}

        {/* ─────────────────────────────────────────────────────────
            STEP 4: REVIEW & BEGIN ("Enter This World")
        ───────────────────────────────────────────────────────── */}
        {currentStep === 4 && (
          <div className="space-y-8 animate-fadeIn">
            <div>
              <span className="text-[10px] uppercase font-mono tracking-widest text-[#C4AD88]">Phase 04 · Review</span>
              <h2 className="font-cinematic text-3xl font-semibold text-[#F1EEE8] mt-1">
                Behold the Threshold Before You
              </h2>
              <p className="text-xs text-[#858A8D] mt-1">
                Your world parameters are engraved. Review your configuration before entering the mist.
              </p>
            </div>

            {/* Featured Preview Card */}
            <div className="overflow-hidden rounded-2xl border border-[#C4AD88]/40 bg-[#171C21] shadow-2xl">
              <div className="relative h-64 w-full overflow-hidden bg-[#101317]">
                <img
                  src={selectedSetting.image}
                  alt={selectedSetting.title}
                  className="h-full w-full object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-[#171C21] via-transparent to-black/40" />

                <div className="absolute top-4 left-4 flex items-center gap-2">
                  <span className="rounded-full bg-[#A33B42] px-3 py-0.5 text-xs font-semibold text-white">
                    {genre}
                  </span>
                  <span className="rounded-md border border-white/20 bg-black/60 px-2 py-0.5 font-cinematic text-xs text-[#C4AD88] backdrop-blur-sm">
                    {selectedSetting.kanji}
                  </span>
                </div>

                <div className="absolute bottom-4 left-6 right-6">
                  <span className="text-[10px] uppercase font-mono tracking-wider text-[#C4AD88]">
                    {season} · {tone} Atmosphere · {selectedSetting.locationName}
                  </span>
                  <h3 className="font-cinematic text-3xl sm:text-4xl font-semibold text-[#F1EEE8] mt-1">
                    {title || 'Untitled Chronicle'}
                  </h3>
                </div>
              </div>

              <div className="p-6 sm:p-8 space-y-6">
                <div>
                  <span className="text-[10px] uppercase font-mono tracking-wider text-[#858A8D] block mb-1">
                    Engraved Premise
                  </span>
                  <p className="font-cinematic text-lg italic text-[#D7DCE0] leading-relaxed">
                    “{premise.trim() || selectedSetting.description}”
                  </p>
                </div>

                {/* Grid Metadata */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs border-t border-white/10 pt-5">
                  <div className="p-3 rounded-lg bg-[#101317] border border-white/5">
                    <span className="text-[#858A8D] block text-[10px] font-mono">Setting</span>
                    <span className="text-[#F1EEE8] font-medium mt-0.5 block">{selectedSetting.title}</span>
                  </div>
                  <div className="p-3 rounded-lg bg-[#101317] border border-white/5">
                    <span className="text-[#858A8D] block text-[10px] font-mono">Genre</span>
                    <span className="text-[#F1EEE8] font-medium mt-0.5 block">{genre}</span>
                  </div>
                  <div className="p-3 rounded-lg bg-[#101317] border border-white/5">
                    <span className="text-[#858A8D] block text-[10px] font-mono">Script</span>
                    <span className="text-[#C4AD88] font-medium mt-0.5 block">{storyLanguage}</span>
                  </div>
                  <div className="p-3 rounded-lg bg-[#101317] border border-white/5">
                    <span className="text-[#858A8D] block text-[10px] font-mono">Scope</span>
                    <span className="text-[#F1EEE8] font-medium mt-0.5 block capitalize">{length}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Submission CTA */}
            <div className="text-center pt-4">
              <button
                type="button"
                disabled={submitting}
                onClick={handleManifestStory}
                className="w-full sm:w-auto inline-flex items-center justify-center gap-3 rounded-xl border border-[#A33B42] bg-[#A33B42] px-10 py-4 text-base font-semibold text-[#F1EEE8] shadow-2xl hover:bg-[#702B34] transition hover:shadow-[0_0_30px_rgba(163,59,66,0.6)] disabled:opacity-50"
              >
                <span>{submitting ? 'Manifesting Sanctuary...' : 'Enter This World'}</span>
                <span className="text-[#C4AD88]">→</span>
              </button>
              <p className="text-[11px] text-[#858A8D] font-mono mt-3">
                Once crossed, every decision leaves a permanent trace.
              </p>
            </div>
          </div>
        )}

        {/* ─────────────────────────────────────────────────────────────
            4. FIXED/BOTTOM STEP WIZARD ACTIONS
        ───────────────────────────────────────────────────────────── */}
        <div className="mt-12 flex items-center justify-between border-t border-white/10 pt-6">
          {currentStep > 1 ? (
            <button
              type="button"
              onClick={goToPrevStep}
              className="flex items-center gap-2 rounded-lg border border-white/10 px-5 py-2.5 text-xs font-medium text-[#858A8D] hover:text-white transition"
            >
              <span>←</span>
              <span>Back</span>
            </button>
          ) : (
            <Link
              to="/dashboard"
              className="flex items-center gap-2 text-xs text-[#858A8D] hover:text-white transition"
            >
              Cancel & Exit
            </Link>
          )}

          {currentStep < 4 && (
            <button
              type="button"
              onClick={goToNextStep}
              className="flex items-center gap-2 rounded-lg border border-[#A33B42] bg-[#A33B42] px-7 py-2.5 text-xs font-semibold text-[#F1EEE8] hover:bg-[#702B34] transition shadow-[0_0_15px_rgba(163,59,66,0.4)]"
            >
              <span>Next Step</span>
              <span>→</span>
            </button>
          )}
        </div>
      </main>
      {/* ─────────────────────────────────────────────────────────────
          5. CUSTOM LOCATION CREATOR & AI IMAGE GENERATION MODAL
      ───────────────────────────────────────────────────────────── */}
      {customModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md overflow-y-auto">
          <div className="relative w-full max-w-2xl rounded-2xl border border-[#C4AD88]/30 bg-[#14191E] p-6 sm:p-8 text-[#F1EEE8] shadow-2xl space-y-6 my-8 animate-fadeIn max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-start justify-between border-b border-white/10 pb-4">
              <div>
                <div className="flex items-center gap-2 text-xs font-mono text-[#C4AD88]">
                  <span className="rounded bg-[#1B2228] px-2 py-0.5 border border-[#C4AD88]/30 font-cinematic">創世 · Genesis</span>
                  <span>Custom World Weaver</span>
                </div>
                <h3 className="font-cinematic text-2xl font-semibold text-[#F1EEE8] mt-1">
                  Forge an Original Sanctuary
                </h3>
                <p className="text-xs text-[#858A8D] mt-0.5">
                  Define an uncatalogued location in Mayoiga and manifest its environmental art.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setCustomModalOpen(false)}
                className="rounded-lg border border-white/10 p-2 text-[#858A8D] hover:text-white hover:border-white/30 transition"
              >
                ✕
              </button>
            </div>

            {/* Form Fields */}
            <div className="space-y-4 text-xs">
              <div>
                <label className="block text-[11px] uppercase tracking-wider text-[#C4AD88] font-mono mb-1.5">
                  Realm / Location Name <span className="text-[#A33B42]">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. The Submerged Bell Tower, Wisteria Pavilion at Twilight"
                  value={customLocForm.name}
                  onChange={(e) => setCustomLocForm((prev) => ({ ...prev, name: e.target.value }))}
                  className="w-full rounded-xl border border-white/10 bg-[#101317] px-4 py-2.5 text-sm font-cinematic text-[#F1EEE8] placeholder-[#858A8D] outline-none focus:border-[#C4AD88]/60 transition"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-[11px] uppercase tracking-wider text-[#C4AD88] font-mono mb-1.5">
                    Atmosphere & Mood
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Eerie, submerged in morning mist, cold rain"
                    value={customLocForm.atmosphere}
                    onChange={(e) => setCustomLocForm((prev) => ({ ...prev, atmosphere: e.target.value }))}
                    className="w-full rounded-xl border border-white/10 bg-[#101317] px-3.5 py-2 text-xs text-[#F1EEE8] placeholder-[#858A8D] outline-none focus:border-[#C4AD88]/60 transition"
                  />
                </div>
                <div>
                  <label className="block text-[11px] uppercase tracking-wider text-[#858A8D] font-mono mb-1.5">
                    Architectural & Visual Cues
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Decaying cedar beams, weathered shoji, water reflections"
                    value={customLocForm.visualDetails}
                    onChange={(e) => setCustomLocForm((prev) => ({ ...prev, visualDetails: e.target.value }))}
                    className="w-full rounded-xl border border-white/10 bg-[#101317] px-3.5 py-2 text-xs text-[#F1EEE8] placeholder-[#858A8D] outline-none focus:border-[#C4AD88]/60 transition"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] uppercase tracking-wider text-[#858A8D] font-mono mb-1.5">
                  Lore & Environmental Description
                </label>
                <textarea
                  rows={2}
                  placeholder="e.g. A half-submerged bell tower at the edge of the cedar lake. When fog rolls down the valley, a deep bronze toll reverberates even with the clapper tied..."
                  value={customLocForm.description}
                  onChange={(e) => setCustomLocForm((prev) => ({ ...prev, description: e.target.value }))}
                  className="w-full rounded-xl border border-white/10 bg-[#101317] px-3.5 py-2 text-xs text-[#F1EEE8] placeholder-[#858A8D] outline-none focus:border-[#C4AD88]/60 transition resize-none"
                />
              </div>
            </div>

            {/* AI Image Generation Section */}
            <div className="rounded-xl border border-white/10 bg-[#101317] p-4 sm:p-5 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/5 pb-3">
                <div>
                  <span className="text-[10px] font-mono uppercase tracking-wider text-[#C4AD88] block">
                    AI Visual Manifestation
                  </span>
                  <h4 className="font-cinematic text-sm font-semibold text-[#F1EEE8]">
                    Environmental Concept Imagery
                  </h4>
                </div>
                <button
                  type="button"
                  disabled={generatingAi}
                  onClick={handleGenerateAiImage}
                  className="inline-flex items-center gap-2 rounded-lg border border-[#A33B42] bg-[#A33B42] px-4 py-2 text-xs font-semibold text-[#F1EEE8] hover:bg-[#702B34] transition disabled:opacity-50 shadow-[0_0_15px_rgba(163,59,66,0.4)]"
                >
                  {generatingAi ? (
                    <>
                      <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent" />
                      <span>Weaving Artwork...</span>
                    </>
                  ) : (
                    <>
                      <span>✨ Generate with AI</span>
                    </>
                  )}
                </button>
              </div>

              {/* Live Preview Container */}
              <div className="relative h-48 w-full overflow-hidden rounded-lg border border-white/10 bg-[#171C21]">
                {customLocForm.image ? (
                  <img
                    src={customLocForm.image}
                    alt={customLocForm.name || 'Custom Location'}
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <div className="flex h-full w-full items-center justify-center text-xs text-[#858A8D]">
                    No image bound yet. Generate with AI or pick a curated anchor below.
                  </div>
                )}
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/20" />
                <div className="absolute bottom-3 left-3 right-3 flex items-end justify-between">
                  <div>
                    <span className="text-[10px] font-mono text-[#C4AD88] uppercase block">
                      Active Environment Art
                    </span>
                    <span className="font-cinematic text-sm text-[#F1EEE8] font-medium">
                      {customLocForm.name.trim() || 'Untitled Sanctuary'}
                    </span>
                  </div>
                  {aiResponseInfo?.success && (
                    <span className="rounded bg-emerald-950/80 border border-emerald-500/40 px-2 py-0.5 text-[10px] font-mono text-emerald-400">
                      ✓ AI Generated ({aiResponseInfo.provider})
                    </span>
                  )}
                </div>
              </div>

              {/* Informative Alert for Missing Provider API Configuration */}
              {aiResponseInfo?.missing_config && (
                <div className="rounded-lg border border-[#A33B42]/50 bg-[#1B1517] p-3.5 text-xs text-[#D7DCE0] space-y-2">
                  <div className="flex items-center gap-2 text-[#C4AD88] font-semibold">
                    <span>⚠️</span>
                    <span>AI Provider Configuration Required for Live Image Model</span>
                  </div>
                  <p className="text-[11px] text-[#858A8D] leading-relaxed">
                    The backend AI image service is connected and ready, but neither <code className="bg-black/50 px-1 py-0.5 rounded text-[#C4AD88]">GEMINI_API_KEY</code> nor <code className="bg-black/50 px-1 py-0.5 rounded text-[#C4AD88]">OPENAI_API_KEY</code> was detected in your <code className="bg-black/50 px-1 py-0.5 rounded text-[#C4AD88]">backend/.env</code>.
                  </p>
                  <div className="rounded bg-black/60 p-2.5 font-mono text-[10px] text-[#858A8D] space-y-1">
                    <div className="text-[#C4AD88]">Prepared Prompt:</div>
                    <div className="text-white/80 italic">"{aiResponseInfo.prompt_used}"</div>
                  </div>
                  <p className="text-[10px] text-[#858A8D]">
                    To enable live Imagen 3 or DALL-E 3, add your API key to <code className="text-[#C4AD88]">backend/.env</code> and restart the server. In the meantime, select any curated high-resolution environmental artwork below!
                  </p>
                </div>
              )}

              {/* Curated Fallback Selection */}
              <div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-[#858A8D] block mb-2">
                  Curated Atmospheric Anchors (Select to Apply Instantly):
                </span>
                <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
                  {curatedAtmospheres.map((atm) => {
                    const isCurrent = customLocForm.image === atm.image
                    return (
                      <button
                        key={atm.id}
                        type="button"
                        onClick={() => {
                          setCustomLocForm((prev) => ({ ...prev, image: atm.image }))
                          setAiResponseInfo(null)
                        }}
                        className={`group relative h-16 rounded-md overflow-hidden border transition ${
                          isCurrent
                            ? 'border-[#C4AD88] ring-1 ring-[#C4AD88]'
                            : 'border-white/10 hover:border-white/30 opacity-70 hover:opacity-100'
                        }`}
                        title={atm.name}
                      >
                        <img src={atm.image} alt={atm.name} className="h-full w-full object-cover" />
                        <div className="absolute inset-0 bg-black/40 group-hover:bg-transparent transition" />
                        <span className="absolute bottom-1 left-1 right-1 text-[8px] font-mono text-white truncate text-center bg-black/70 px-1 rounded">
                          {atm.name.split(' ')[0]}
                        </span>
                      </button>
                    )
                  })}
                </div>
              </div>
            </div>

            {/* Modal Actions */}
            <div className="flex items-center justify-end gap-3 border-t border-white/10 pt-4">
              <button
                type="button"
                onClick={() => setCustomModalOpen(false)}
                className="rounded-lg border border-white/10 px-4 py-2 text-xs font-medium text-[#858A8D] hover:text-white transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleAcceptCustomLocation}
                className="rounded-lg border border-[#C4AD88] bg-[#C4AD88] px-6 py-2 text-xs font-semibold text-[#101317] hover:bg-[#d6c29e] transition shadow-[0_0_15px_rgba(196,173,136,0.3)]"
              >
                Accept & Bind Realm
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  )
}
