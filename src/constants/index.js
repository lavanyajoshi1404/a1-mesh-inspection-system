import {
  LayoutDashboard, Eye, Table, BarChart2, BookOpen, FileText,
} from 'lucide-react';

export const PRODUCT_PROFILES = [
  {
    id: 'P001',
    name: 'Product 1',
    wire_diameter_mm: 4.0,
    aperture_h_mm: 12.7,
    aperture_v_mm: 76.2,
    standards: 'BS 1722-14 / EN 10223-7',
    coating: 'Hot-Dip Galvanized + Thermoplastic',
    description: 'High-security anti-climb and anti-cut perimeter fence with finger-proof aperture spacing.',
  },
  {
    id: 'P002',
    name: 'Product 2',
    wire_diameter_mm: '8.0H / 6.0V',
    aperture_h_mm: 50.0,
    aperture_v_mm: 200.0,
    standards: 'EN 10223-7 / ISO 9001',
    coating: 'Galvanized + Polyester Powder Coated',
    description: 'Heavy-duty double horizontal wire mesh panel engineered for critical infrastructure.',
  },
  {
    id: 'P003',
    name: 'Product 3',
    wire_diameter_mm: '4.0 / 5.0',
    aperture_h_mm: 50.0,
    aperture_v_mm: 200.0,
    standards: 'EN 10223-7 / DIN 50021',
    coating: 'Polyester Powder Coated (Min 60μm)',
    description: 'V-beam reinforced modular wire mesh fencing for industrial boundaries.',
  },
];

export const NAVIGATION_ITEMS = [
  { id: 'qcdashboard',  icon: LayoutDashboard, label: 'Quality Check' },
  { id: 'visual',       icon: Eye,             label: 'Visual Inspection' },
  { id: 'measurements', icon: Table,           label: 'Measurements & Findings' },
  { id: 'analytics',    icon: BarChart2,       label: 'Yield Analytics' },
  { id: 'products',     icon: BookOpen,        label: 'Product Profiles' },
  { id: 'report',       icon: FileText,        label: 'Compliance Certificate' },
];

export const VISUALIZATION_MODES = ['ORIGINAL', 'GRID', 'INTERSECTIONS', 'HEATMAP', 'SPACING'];
