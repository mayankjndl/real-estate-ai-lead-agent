// src/lib/api/mockTwinService.ts
// IREIOS 4.0 Day-1 mock — 1 project / 2 towers / 10 floors / 2 units = 40

export type UnitStatus = 'Available' | 'Hold' | 'Sold';

export interface UnitData {
  id: string;
  unit_number: string;
  status: UnitStatus;
  price: number;
  bhk: string;
  floor: number;
  customer?: string;
  leadScore?: number;
}

export interface TowerData {
  id: string;
  name: string;
  units: UnitData[][]; // floors -> units
}

export interface ProjectData {
  id: string;
  name: string;
  towers: TowerData[];
}

/** Align with GET /api/v1/inventory/twin seed (The Summit, 40 units). */
export const generateMockTwinData = (): ProjectData => {
  const towers: TowerData[] = [];
  const floorsCount = 10;
  const unitsPerFloor = 2;
  const names = ['John Doe', 'Sarah Connor', 'Michael Smith', 'Emma Johnson', undefined];

  ['Tower A', 'Tower B'].forEach((towerName, tIdx) => {
    const letter = towerName.split(' ')[1];
    const towerId = `tw:tower-${letter.toLowerCase()}`;
    const floors: UnitData[][] = [];

    for (let f = 1; f <= floorsCount; f++) {
      const floorUnits: UnitData[] = [];
      for (let u = 1; u <= unitsPerFloor; u++) {
        const unitNum = `${letter}-${f}0${u}`;
        const unitId = `unit:mock-${letter}-${f}-${u}`;
        const rand = (tIdx * 20 + f * 2 + u) % 100;
        let status: UnitStatus = 'Available';
        let customer: string | undefined;
        let leadScore: number | undefined;

        if (rand > 74) {
          status = 'Sold';
          customer = names[rand % (names.length - 1)];
        } else if (rand > 49) {
          status = 'Hold';
          customer = names[rand % (names.length - 1)];
          leadScore = 60 + (rand % 40);
        }

        floorUnits.push({
          id: unitId,
          unit_number: unitNum,
          status,
          price: 12_000_000 + ((f * 100_000 + u * 50_000) % 13_000_000),
          bhk: `${2 + (u % 3)}`,
          floor: f,
          customer,
          leadScore,
        });
      }
      floors.push(floorUnits);
    }

    towers.push({ id: towerId, name: towerName, units: floors });
  });

  return {
    id: 'prj:the-summit',
    name: 'The Summit',
    towers,
  };
};

/** Contract-shaped payload matching backend twin API. */
export const mockTwinApiResponse = {
  status: 'success',
  disclaimer: 'Demo inventory layout',
  available: true,
  project: {
    id: 'prj:the-summit',
    name: 'The Summit',
    location: 'Downtown',
  },
  towers: generateMockTwinData().towers.map((t) => ({
    id: t.id,
    name: t.name,
    floors: t.units.map((floorUnits, idx) => ({
      level: idx + 1,
      units: floorUnits.map((u) => ({
        id: u.id,
        unit_number: u.unit_number,
        status: u.status.toLowerCase() as 'available' | 'hold' | 'sold',
        price: u.price,
        currency: 'INR',
        bhk: u.bhk,
        lead_id: null,
      })),
    })),
  })),
  counts: { available: 20, hold: 10, sold: 10 },
};
