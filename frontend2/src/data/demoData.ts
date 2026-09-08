export type Spill = {
  id: number;
  name: string;
  position: [number, number];
  origin: [number, number];
  area: string;
  confidence: string;
  risk: string;
  polygon: [number, number][];
  drift: [number, number][];
};

export type Vessel = {
  id: number;
  name: string;
  position: [number, number];
  type: string;
  status: string;
};

export const spills: Spill[] = [
  {
    id: 1,
    name: "Arabian Sea Spill",
    position: [15.2, 63.5],
    origin: [15.8, 62.9],
    area: "24.6 km²",
    confidence: "94%",
    risk: "HIGH",
    polygon: [
      [15.8, 62.8],
      [16.1, 63.5],
      [15.5, 64.2],
      [14.7, 64.0],
      [14.4, 63.3],
      [14.9, 62.7],
    ],
    drift: [
      [15.2, 63.5],
      [14.8, 64.0],
      [14.3, 64.5],
      [13.8, 65.0],
    ],
  },

  {
    id: 2,
    name: "Gulf of Mexico Spill",
    position: [25.5, -90.2],
    origin: [26.0, -90.7],
    area: "18.2 km²",
    confidence: "91%",
    risk: "MEDIUM",
    polygon: [
      [26.1, -90.8],
      [26.3, -90.0],
      [25.7, -89.5],
      [24.9, -89.8],
      [24.8, -90.6],
      [25.4, -91.0],
    ],
    drift: [
      [25.5, -90.2],
      [25.0, -89.8],
      [24.5, -89.4],
      [24.0, -89.0],
    ],
  },

  {
    id: 3,
    name: "South China Sea Spill",
    position: [12.4, 114.8],
    origin: [13.0, 114.2],
    area: "31.8 km²",
    confidence: "96%",
    risk: "CRITICAL",
    polygon: [
      [13.1, 114.1],
      [13.3, 114.9],
      [12.8, 115.5],
      [11.9, 115.4],
      [11.6, 114.6],
      [12.1, 114.0],
    ],
    drift: [
      [12.4, 114.8],
      [12.0, 115.3],
      [11.6, 115.8],
      [11.2, 116.3],
    ],
  },

  {
    id: 4,
    name: "North Atlantic Spill",
    position: [38.5, -35.2],
    origin: [39.0, -35.8],
    area: "12.4 km²",
    confidence: "89%",
    risk: "MEDIUM",
    polygon: [
      [39.0, -35.8],
      [39.2, -35.1],
      [38.7, -34.5],
      [37.9, -34.7],
      [37.7, -35.5],
      [38.2, -36.0],
    ],
    drift: [
      [38.5, -35.2],
      [39.0, -34.8],
      [39.5, -34.4],
      [40.0, -34.0],
    ],
  },

  {
    id: 5,
    name: "Indian Ocean Spill",
    position: [-8.5, 78.2],
    origin: [-8.0, 77.7],
    area: "9.7 km²",
    confidence: "93%",
    risk: "HIGH",
    polygon: [
      [-7.9, 77.6],
      [-7.7, 78.4],
      [-8.2, 78.9],
      [-9.0, 78.8],
      [-9.3, 78.0],
      [-8.8, 77.5],
    ],
    drift: [
      [-8.5, 78.2],
      [-8.9, 78.7],
      [-9.3, 79.2],
      [-9.7, 79.7],
    ],
  },
];

export const vessels: Vessel[] = [
  {
    id: 1,
    name: "MV Ocean Star",
    position: [15.8, 63.2],
    type: "Oil Tanker",
    status: "Underway",
  },

  {
    id: 2,
    name: "MV Pacific Trader",
    position: [12.8, 114.2],
    type: "Cargo Ship",
    status: "Underway",
  },

  {
    id: 3,
    name: "MV Atlantic Carrier",
    position: [25.0, -89.5],
    type: "Oil Tanker",
    status: "Underway",
  },

  {
    id: 4,
    name: "MV Indian Voyager",
    position: [-8.0, 78.8],
    type: "Cargo Ship",
    status: "Underway",
  },
];