import { VenueInfo } from "../types";

export const TAIPEI_VENUES: Record<string, VenueInfo> = {
  hotel_ximen: {
    id: "hotel_ximen",
    name: "Hotel (Ximending)",
    lat: 25.0422,
    lon: 121.5079,
    indoor: true,
    tags: ["hotel"],
    cost: 0,
    walk: 0,
    open: "00:00",
    close: "23:59",
    min_minutes: 0,
    description: "Trip basecamp: cozy hotel located in central Ximending."
  },
  din_tai_fung_101: {
    id: "din_tai_fung_101",
    name: "Din Tai Fung @ Taipei 101",
    lat: 25.0336,
    lon: 121.5648,
    indoor: true,
    tags: ["food"],
    cost: 1200,
    walk: 0,
    open: "11:00",
    close: "21:30",
    min_minutes: 60,
    description: "Flagship Michelin-recommended dumpling restaurant inside Taipei 101 Mall."
  },
  taipei101_observatory: {
    id: "taipei101_observatory",
    name: "Taipei 101 Observatory",
    lat: 25.0339,
    lon: 121.5645,
    indoor: true,
    tags: ["scenic"],
    cost: 600,
    walk: 0,
    open: "10:00",
    close: "22:00",
    min_minutes: 60,
    description: "Indoor observation deck on the 89th floor with panoramic city views."
  },
  elephant_mountain: {
    id: "elephant_mountain",
    name: "Elephant Mountain Trail",
    lat: 25.0273,
    lon: 121.5764,
    indoor: false,
    tags: ["hiking", "scenic"],
    cost: 0,
    walk: 3,
    open: "05:00",
    close: "22:00",
    min_minutes: 90,
    description: "Iconic stair trail offering premier viewpoints of Taipei 101 skyline."
  },
  yangmingshan: {
    id: "yangmingshan",
    name: "Yangmingshan Qixing Trail",
    lat: 25.1559,
    lon: 121.5482,
    indoor: false,
    tags: ["hiking", "nature"],
    cost: 0,
    walk: 3,
    open: "06:00",
    close: "18:00",
    min_minutes: 180,
    description: "Volcanic peak trail with mountain vents in Yangmingshan National Park."
  },
  fine_arts_museum: {
    id: "fine_arts_museum",
    name: "Taipei Fine Arts Museum",
    lat: 25.0726,
    lon: 121.5246,
    indoor: true,
    tags: ["museum", "art"],
    cost: 30,
    walk: 1,
    open: "09:30",
    close: "17:30",
    min_minutes: 90,
    description: "Modern and contemporary art museum featuring international exhibits."
  },
  moca_taipei: {
    id: "moca_taipei",
    name: "MoCA Taipei",
    lat: 25.0503,
    lon: 121.5195,
    indoor: true,
    tags: ["museum", "art"],
    cost: 100,
    walk: 0,
    open: "10:00",
    close: "18:00",
    min_minutes: 60,
    description: "Historic red-brick building hosting experimental contemporary art."
  },
  national_palace_museum: {
    id: "national_palace_museum",
    name: "National Palace Museum",
    lat: 25.1024,
    lon: 121.5485,
    indoor: true,
    tags: ["museum", "history"],
    cost: 350,
    walk: 1,
    open: "09:00",
    close: "17:00",
    min_minutes: 120,
    description: "World-renowned repository of imperial Chinese history and ancient artworks."
  },
  huashan_park: {
    id: "huashan_park",
    name: "Huashan 1914 Creative Park",
    lat: 25.0441,
    lon: 121.5294,
    indoor: true,
    tags: ["art", "shopping"],
    cost: 0,
    walk: 1,
    open: "10:00",
    close: "20:00",
    min_minutes: 60,
    description: "Converted historic winery hosting indoor creative exhibitions and design pop-ups."
  },
  songshan_park: {
    id: "songshan_park",
    name: "Songshan Cultural and Creative Park",
    lat: 25.0437,
    lon: 121.5606,
    indoor: true,
    tags: ["art", "design"],
    cost: 0,
    walk: 1,
    open: "09:00",
    close: "18:00",
    min_minutes: 60,
    description: "Former tobacco factory revitalized as a cultural and design laboratory."
  },
  eslite_xinyi: {
    id: "eslite_xinyi",
    name: "Eslite Bookstore Xinyi",
    lat: 25.0393,
    lon: 121.5658,
    indoor: true,
    tags: ["shopping", "books"],
    cost: 0,
    walk: 0,
    open: "11:00",
    close: "22:00",
    min_minutes: 45,
    description: "Multi-level flagship bookstore, vinyl record lounge, and lifestyle boutique."
  },
  cafe_simple_kaffa: {
    id: "cafe_simple_kaffa",
    name: "Simple Kaffa",
    lat: 25.0443,
    lon: 121.5300,
    indoor: true,
    tags: ["cafe"],
    cost: 200,
    walk: 0,
    open: "10:00",
    close: "18:00",
    min_minutes: 45,
    description: "World Barista Championship winner specialty pour-over coffee house."
  },
  cafe_fujin: {
    id: "cafe_fujin",
    name: "Fujin Tree Cafe",
    lat: 25.0601,
    lon: 121.5579,
    indoor: true,
    tags: ["cafe"],
    cost: 250,
    walk: 0,
    open: "10:00",
    close: "19:00",
    min_minutes: 60,
    description: "Chic tree-lined neighborhood cafe serving artisan roasts and pastries."
  },
  longshan_temple: {
    id: "longshan_temple",
    name: "Longshan Temple",
    lat: 25.0372,
    lon: 121.4999,
    indoor: false,
    tags: ["culture", "temple"],
    cost: 0,
    walk: 0,
    open: "06:00",
    close: "22:00",
    min_minutes: 45,
    description: "Historic folk temple courtyard with over 280 years of cultural heritage."
  }
};

export function getVenue(id: string, venuesMap?: Record<string, VenueInfo>): VenueInfo {
  if (venuesMap && venuesMap[id]) {
    return venuesMap[id];
  }

  // Derive reference coordinates from current venuesMap if available
  let refLat = 0;
  let refLon = 0;
  if (venuesMap && Object.values(venuesMap).length > 0) {
    const firstV = Object.values(venuesMap)[0];
    if (firstV && firstV.lat) {
      refLat = firstV.lat;
      refLon = firstV.lon;
    }
  }

  return {
    id,
    name: id.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
    lat: refLat,
    lon: refLon,
    indoor: true,
    tags: [],
    cost: 0,
    walk: 0,
    open: "09:00",
    close: "21:30",
    min_minutes: 45,
    description: ""
  };
}

export function getGroupColor(members: string[], trackIndex: number = 0): {
  badge: string;
  bg: string;
  border: string;
  text: string;
  pill: string;
  name: string;
} {
  const memberLabel = members.length > 0 ? members.join(", ") : "All Travelers";
  const palettes = [
    {
      badge: `Track 1 · ${memberLabel}`,
      name: "Track 1",
      bg: "bg-emerald-950/20",
      border: "border-emerald-500/40",
      text: "text-emerald-600",
      pill: "bg-emerald-500/10 text-emerald-700 border-emerald-500/30"
    },
    {
      badge: `Track 2 · ${memberLabel}`,
      name: "Track 2",
      bg: "bg-indigo-950/20",
      border: "border-indigo-500/40",
      text: "text-indigo-600",
      pill: "bg-indigo-500/10 text-indigo-700 border-indigo-500/30"
    },
    {
      badge: `Track 3 · ${memberLabel}`,
      name: "Track 3",
      bg: "bg-amber-950/20",
      border: "border-amber-500/40",
      text: "text-amber-600",
      pill: "bg-amber-500/10 text-amber-700 border-amber-500/30"
    },
    {
      badge: `Track 4 · ${memberLabel}`,
      name: "Track 4",
      bg: "bg-rose-950/20",
      border: "border-rose-500/40",
      text: "text-rose-600",
      pill: "bg-rose-500/10 text-rose-700 border-rose-500/30"
    }
  ];
  return palettes[trackIndex % palettes.length];
}
