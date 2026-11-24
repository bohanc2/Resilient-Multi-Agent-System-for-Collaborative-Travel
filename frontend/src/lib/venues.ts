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
    description: "旅程起訖點：位於西門町中心的舒適旅店。"
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
    description: "台北 101 旗艦店小籠包晚餐，米其林推薦經典美食。"
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
    description: "89 樓室內觀景台，俯瞰台北盆地璀璨天際線。"
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
    description: "象山巨石步道，眺望台北 101 最壯麗的制高點。"
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
    description: "陽明山七星山主東峰步道，大屯火山群地質景觀。"
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
    description: "北美館：台灣首座現代美術館，當代前衛策展。"
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
    description: "台北當代藝術館：紅磚歷史古蹟結合前衛新媒體藝術展覽。"
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
    description: "國立故宮博物院：世界級中華歷史藝術瑰寶典藏。"
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
    description: "華山 1914 文創園區：舊酒廠改造的室內展覽空間與特色選品店。"
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
    description: "松山文創園區：松菸菸廠古蹟再造之設計與當代展演工坊。"
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
    description: "誠品信義生活館：多樓層書籍展館、黑膠音樂與文創設計空間。"
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
    description: "興波咖啡旗艦店：WBC 世界冠軍手沖精品咖啡。"
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
    description: "富錦樹咖啡：民生社區綠意街景與慢活手作甜點。"
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
    description: "艋舺龍山寺：兩百多年歷史之國家二級古蹟古寺。"
  }
};

export function getVenue(id: string): VenueInfo {
  return TAIPEI_VENUES[id] || {
    id,
    name: id,
    lat: 25.033,
    lon: 121.564,
    indoor: true,
    tags: [],
    cost: 0,
    walk: 0,
    open: "09:00",
    close: "21:00",
    min_minutes: 45,
    description: ""
  };
}

export function getGroupColor(members: string[]): {
  badge: string;
  bg: string;
  border: string;
  text: string;
  pill: string;
  name: string;
} {
  const set = new Set(members);
  if (set.has("Alice") || set.has("Bob")) {
    return {
      badge: "登山健行組",
      name: "登山組",
      bg: "bg-emerald-950/20",
      border: "border-emerald-500/40",
      text: "text-emerald-400",
      pill: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30"
    };
  }
  if (set.has("Carol") || set.has("Dave")) {
    return {
      badge: "藝文探索組",
      name: "藝文組",
      bg: "bg-indigo-950/20",
      border: "border-indigo-500/40",
      text: "text-indigo-400",
      pill: "bg-indigo-500/10 text-indigo-300 border-indigo-500/30"
    };
  }
  if (set.has("Eve") || set.has("Frank")) {
    return {
      badge: "咖啡文青組",
      name: "咖啡組",
      bg: "bg-amber-950/20",
      border: "border-amber-500/40",
      text: "text-amber-400",
      pill: "bg-amber-500/10 text-amber-300 border-amber-500/30"
    };
  }
  return {
    badge: "全員合流",
    name: "全員",
    bg: "bg-amber-500/10",
    border: "border-amber-400/50",
    text: "text-amber-300",
    pill: "bg-amber-400/20 text-amber-200 border-amber-400/40"
  };
}
