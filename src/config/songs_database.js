/**
 * Children's Cartoon Nursery Rhymes & Educational Songs Database
 * Curated with rhyming verses, musical pacing, cartoon character descriptions, and SEO tags.
 */

const SONGS_DATABASE = [
  {
    id: 'wheels-on-the-bus',
    title: 'The Wheels on the Bus',
    subtitle: 'Animal Safari Bus Adventure',
    theme: 'vehicles',
    bpm: 115,
    musicalStyle: 'bounce',
    mood: 'upbeat, joyful, bouncy',
    characterHero: 'yellow_bus_with_animals',
    colorPalette: {
      sky: ['#4FC3F7', '#B3E5FC'],
      ground: ['#81C784', '#4CAF50'],
      primary: '#FDD835',
      accent: '#E53935'
    },
    verses: [
      {
        verseNumber: 1,
        lyrics: "The wheels on the bus go round and round, round and round, round and round! The wheels on the bus go round and round, all through the town!",
        sceneDescription: "Cheerful yellow cartoon school bus rolling down a sunny hillside road with smiling bear driving."
      },
      {
        verseNumber: 2,
        lyrics: "The wipers on the bus go swish swish swish, swish swish swish, swish swish swish! The wipers on the bus go swish swish swish, all through the town!",
        sceneDescription: "Playful wipers swishing with gentle raindrop sparkles and a cheerful smiling bunny looking out the window."
      },
      {
        verseNumber: 3,
        lyrics: "The horn on the bus goes beep beep beep, beep beep beep, beep beep beep! The horn on the bus goes beep beep beep, all through the town!",
        sceneDescription: "Friendly cartoon lion cub pressing the horn with big musical notes floating out into the blue sky."
      },
      {
        verseNumber: 4,
        lyrics: "The monkeys on the bus go jump jump jump, jump jump jump, jump jump jump! The monkeys on the bus go jump jump jump, all through the town!",
        sceneDescription: "Three cute baby monkeys happily hopping up and down on the bus seats waving to little birds outside."
      }
    ],
    seoKeywords: ['wheels on the bus', 'nursery rhymes', 'bus song for kids', 'cartoon bus', 'toddler songs']
  },
  {
    id: 'old-macdonald-farm',
    title: "Old MacDonald Had a Farm",
    subtitle: 'Sing-Along Animal Sounds',
    theme: 'animals',
    bpm: 110,
    musicalStyle: 'adventure',
    mood: 'playful, rhythmic, interactive',
    characterHero: 'friendly_cow_and_farmer',
    colorPalette: {
      sky: ['#29B6F6', '#E1F5FE'],
      ground: ['#9CCC65', '#558B2F'],
      primary: '#FF7043',
      accent: '#FFD54F'
    },
    verses: [
      {
        verseNumber: 1,
        lyrics: "Old MacDonald had a farm, E-I-E-I-O! And on that farm he had a cow, E-I-E-I-O! With a moo moo here and a moo moo there! Here a moo, there a moo, everywhere a moo moo! Old MacDonald had a farm, E-I-E-I-O!",
        sceneDescription: "Cute spotted black and white baby cow chewing sweet green clover beside a bright red barn."
      },
      {
        verseNumber: 2,
        lyrics: "Old MacDonald had a farm, E-I-E-I-O! And on that farm he had a duck, E-I-E-I-O! With a quack quack here and a quack quack there! Here a quack, there a quack, everywhere a quack quack! Old MacDonald had a farm, E-I-E-I-O!",
        sceneDescription: "Fluffy yellow duckling swimming in a crystal blue sparkling pond with pink water lilies."
      },
      {
        verseNumber: 3,
        lyrics: "Old MacDonald had a farm, E-I-E-I-O! And on that farm he had a pig, E-I-E-I-O! With an oink oink here and an oink oink there! Here an oink, there an oink, everywhere an oink oink! Old MacDonald had a farm, E-I-E-I-O!",
        sceneDescription: "Happy pink piggy splashing in a warm bubble puddle wearing a little sunflower hat."
      },
      {
        verseNumber: 4,
        lyrics: "Old MacDonald had a farm, E-I-E-I-O! And on that farm he had a sheep, E-I-E-I-O! With a baa baa here and a baa baa there! Here a baa, there a baa, everywhere a baa baa! Old MacDonald had a farm, E-I-E-I-O!",
        sceneDescription: "Fluffy white lamb dancing in a meadow of colorful daisies under a smiling golden sun."
      }
    ],
    seoKeywords: ['old macdonald had a farm', 'animal sounds song', 'farm animals for kids', 'preschool songs']
  },
  {
    id: 'baby-dino-dance',
    title: 'Baby Dino Stomp & Dance',
    subtitle: 'Playful Dinosaur Groove',
    theme: 'dinosaurs',
    bpm: 120,
    musicalStyle: 'bounce',
    mood: 'energetic, catchy, active',
    characterHero: 'cute_green_t_rex',
    colorPalette: {
      sky: ['#80DEEA', '#E0F7FA'],
      ground: ['#66BB6A', '#388E3C'],
      primary: '#43A047',
      accent: '#FFA726'
    },
    verses: [
      {
        verseNumber: 1,
        lyrics: "Stomp stomp stomp goes the baby dinosaur! Roar roar roar let us hear your happy roar! Shake your tail and wiggle your toes, that is how the dino dance goes!",
        sceneDescription: "Cute baby green T-Rex wearing tiny blue sneakers stomping happily across a prehistoric jungle playground."
      },
      {
        verseNumber: 2,
        lyrics: "Flap flap flap goes the pterodactyl friend! Flying through the clouds till the day comes to an end! Wave your hands way up high, soaring like a bird in the sunny blue sky!",
        sceneDescription: "Friendly purple pterodactyl with big cartoon eyes doing joyful loops through puffy white clouds."
      },
      {
        verseNumber: 3,
        lyrics: "Chomp chomp chomp yummy leaves upon the tree! Brontosaurus smiles and is happy as can be! Eat your greens to grow up strong, come and sing the dinosaur song!",
        sceneDescription: "Gentle turquoise long-neck brontosaurus munching yummy green cartoon leaves with a cheerful smile."
      }
    ],
    seoKeywords: ['dinosaur song', 'baby dino dance', 'stomp and roar', 'dino songs for children', 'toddler dance']
  },
  {
    id: 'colors-of-the-rainbow',
    title: 'The Colors of the Rainbow',
    subtitle: 'Learn Colors Sing-Along',
    theme: 'colors',
    bpm: 108,
    musicalStyle: 'learning',
    mood: 'sweet, educational, cheerful',
    characterHero: 'rainbow_chameleon_and_butterflies',
    colorPalette: {
      sky: ['#CE93D8', '#F3E5F5'],
      ground: ['#FFF59D', '#FFE082'],
      primary: '#AB47BC',
      accent: '#FF4081'
    },
    verses: [
      {
        verseNumber: 1,
        lyrics: "Red is an apple sweet and round! Red is a strawberry on the ground! Red red red is a lovely sight, shining bright in the warm sunlight!",
        sceneDescription: "Lush cartoon orchard with big smiling bright red apples and playful red ladybugs."
      },
      {
        verseNumber: 2,
        lyrics: "Yellow is the sun shining up above! Yellow is a banana that we all love! Yellow yellow yellow like a little chick, let's learn colors nice and quick!",
        sceneDescription: "Golden sunny scene with a cheerful little yellow chick pecking near yummy yellow bananas."
      },
      {
        verseNumber: 3,
        lyrics: "Blue is the ocean wide and deep! Blue is the sky before we sleep! Blue blue blue like a dolphin play, splashing around on a happy day!",
        sceneDescription: "Vibrant ocean waves with a cute cartoon blue dolphin jumping over sparkling turquoise water."
      },
      {
        verseNumber: 4,
        lyrics: "Green is the grass where bunnies run! Green is the tree having so much fun! Red, yellow, blue, and green so bright, a rainbow of colors brings delight!",
        sceneDescription: "Vibrant giant rainbow arching across rolling hills with joyful cartoon animal friends celebrating together."
      }
    ],
    seoKeywords: ['colors song for toddlers', 'learn colors', 'rainbow song for kids', 'preschool color learning']
  },
  {
    id: 'five-little-ducks',
    title: 'Five Little Ducks Went Swimming One Day',
    subtitle: 'Fun Counting Nursery Rhyme',
    theme: 'counting',
    bpm: 112,
    musicalStyle: 'adventure',
    mood: 'catchy, counting, storytelling',
    characterHero: 'mother_duck_and_ducklings',
    colorPalette: {
      sky: ['#64B5F6', '#BBDEFB'],
      ground: ['#81C784', '#388E3C'],
      primary: '#FFEE58',
      accent: '#FB8C00'
    },
    verses: [
      {
        verseNumber: 1,
        lyrics: "Five little ducks went out one day, over the hills and far away! Mother duck said quack quack quack quack, but only four little ducks came back!",
        sceneDescription: "Proud mother duck with floral bonnet leading five fluffy yellow ducklings paddling across a sparkling lake."
      },
      {
        verseNumber: 2,
        lyrics: "Four little ducks went out one day, over the hills and far away! Mother duck said quack quack quack quack, but only three little ducks came back!",
        sceneDescription: "Four ducklings splashing and chasing colorful bubbles over soft green rolling hills."
      },
      {
        verseNumber: 3,
        lyrics: "Three little ducks went out one day, over the hills and far away! Mother duck said quack quack quack quack, but only two little ducks came back!",
        sceneDescription: "Three ducklings discovering a friendly green turtle smiling on a mossy cartoon rock."
      },
      {
        verseNumber: 4,
        lyrics: "Sad mother duck went out one day, over the hills and far away! Mother duck said QUACK QUACK QUACK QUACK, and all five little ducks came swimming right back!",
        sceneDescription: "Huge joyful celebration with all five ducklings hugging mother duck with heart bubbles and sparkles."
      }
    ],
    seoKeywords: ['five little ducks', 'counting song for kids', 'duck song', 'nursery rhymes for babies']
  },
  {
    id: 'twinkle-twinkle-lullaby',
    title: 'Twinkle Twinkle Little Star',
    subtitle: 'Sweet Bedtime Lullaby',
    theme: 'bedtime',
    bpm: 78,
    musicalStyle: 'lullaby',
    mood: 'gentle, soothing, magical, calm',
    characterHero: 'glowing_star_and_sleepy_bear',
    colorPalette: {
      sky: ['#1A237E', '#283593'],
      ground: ['#303F9F', '#1A237E'],
      primary: '#FFF59D',
      accent: '#80DEEA'
    },
    verses: [
      {
        verseNumber: 1,
        lyrics: "Twinkle twinkle little star, how I wonder what you are! Up above the world so high, like a diamond in the sky! Twinkle twinkle little star, how I wonder what you are!",
        sceneDescription: "Magical night sky with a smiling crescent moon, glowing golden star with cute wink, and soft fluffy purple clouds."
      },
      {
        verseNumber: 2,
        lyrics: "When the blazing sun is gone, when he nothing shines upon, then you show your little light, twinkle twinkle all the night! Twinkle twinkle little star, how I wonder what you are!",
        sceneDescription: "Cute sleepy brown bear cub tucked under a star-patterned quilt sleeping peacefully by a moonlit window."
      }
    ],
    seoKeywords: ['twinkle twinkle little star', 'bedtime lullaby for babies', 'sleep music for toddlers', 'baby bedtime song']
  },
  {
    id: 'alphabet-safari-song',
    title: 'The Alphabet Safari Song',
    subtitle: 'ABC Phonics Sing-Along',
    theme: 'alphabet',
    bpm: 114,
    musicalStyle: 'learning',
    mood: 'bright, educational, upbeat',
    characterHero: 'safari_lion_with_abc_blocks',
    colorPalette: {
      sky: ['#4DD0E1', '#E0F7FA'],
      ground: ['#DCE775', '#9E9D24'],
      primary: '#FF8A65',
      accent: '#26C6DA'
    },
    verses: [
      {
        verseNumber: 1,
        lyrics: "A is for Alligator, B is for Bear! C is for Cat with soft cuddly hair! D is for Dog who loves to play! E is for Elephant having a great day! Sing your ABCs with me, happy as can be!",
        sceneDescription: "Bright colorful wooden alphabet blocks A-B-C-D-E stacked with cute smiling animals peeking behind them."
      },
      {
        verseNumber: 2,
        lyrics: "F is for Fish swimming in the sea! G is for Giraffe as tall as a tree! H is for Horse running fast and free! I is for Iguana looking at me! Come and sing the safari rhyme, we are having such a good time!",
        sceneDescription: "Gentle tall giraffe wearing a yellow scarf smiling beside a cheerful green iguana under an acacia tree."
      }
    ],
    seoKeywords: ['alphabet song', 'abc phonics for kids', 'learn abc', 'preschool alphabet rhyme', 'kindergarten songs']
  },
  {
    id: 'happy-and-you-know-it',
    title: 'If You Are Happy and You Know It',
    subtitle: 'Action Dance Song for Kids',
    theme: 'action_dance',
    bpm: 118,
    musicalStyle: 'bounce',
    mood: 'interactive, active, energetic',
    characterHero: 'dancing_toddlers_and_animals',
    colorPalette: {
      sky: ['#FFB74D', '#FFF3E0'],
      ground: ['#81C784', '#43A047'],
      primary: '#FF5722',
      accent: '#00E676'
    },
    verses: [
      {
        verseNumber: 1,
        lyrics: "If you're happy and you know it clap your hands! If you're happy and you know it clap your hands! If you're happy and you know it and you really want to show it, if you're happy and you know it clap your hands!",
        sceneDescription: "Joyful cartoon animal friends clapping paws together in time with big sparkling musical notes."
      },
      {
        verseNumber: 2,
        lyrics: "If you're happy and you know it stomp your feet! If you're happy and you know it stomp your feet! If you're happy and you know it and you really want to show it, if you're happy and you know it stomp your feet!",
        sceneDescription: "Cute baby elephant and baby hippo happily stomping little feet on a colorful dance floor."
      },
      {
        verseNumber: 3,
        lyrics: "If you're happy and you know it shout HURRAY! If you're happy and you know it shout HURRAY! If you're happy and you know it and you really want to show it, if you're happy and you know it shout HURRAY!",
        sceneDescription: "Colorful confetti explosion with smiling cartoon kids and animals cheering happily together."
      }
    ],
    seoKeywords: ['if you are happy and you know it', 'action song for kids', 'dance along songs', 'preschool movement song']
  }
];

function getSongById(id) {
  return SONGS_DATABASE.find(s => s.id === id);
}

function getAllSongs() {
  return SONGS_DATABASE;
}

function getRandomSongs(count = 5) {
  const shuffled = [...SONGS_DATABASE].sort(() => 0.5 - Math.random());
  return shuffled.slice(0, Math.min(count, SONGS_DATABASE.length));
}

module.exports = {
  SONGS_DATABASE,
  getSongById,
  getAllSongs,
  getRandomSongs
};
