export type Event = { day: string; meta: string; title: string; place: string; detail: string; url: string };
export type Member = { name: string; role: string; image: string };
export type Plan = { name: string; price: string; summary: string; benefits: string[] };
export type Issue = { title: string; image: string };

export const events: Event[] = [
  { day: '26', meta: 'Sept · Sat', title: 'Empowering Wellness Expo', place: 'The Connection, Rhodes', detail: 'A free day for the whole family.', url: 'https://www.empowhersydney.com/event-details/empowering-wellness-expo-a-fun-day-for-the-whole-family' },
  { day: '14', meta: 'Oct · Wed', title: 'Coffee Meetup for Women 50plus', place: 'Cafe Botanica', detail: 'A relaxed morning out.', url: 'https://www.empowhersydney.com/event-details/empowher-coffee-meetup-for-women-50plus' },
  { day: '15', meta: 'Oct · Thu', title: 'R U OK? Youth Mental Health Day', place: 'Hong Kong', detail: "It's okay to not be okay.", url: 'https://www.empowhersydney.com/event-details/hong-kong-ruok-youth-mental-health' },
];

export const members: Member[] = [
  { name: 'Sharon Zhang', role: 'Vice Chairwoman', image: 'sharon-s' },
  { name: 'Tina Wu', role: 'Founder of Bloom Naturals', image: 'tina' },
  { name: 'Jacqueline Lo', role: 'Founder of Yu Liang Pty Ltd', image: 'jacq' },
  { name: 'Rachel WingMan', role: 'Founder of Wonderlab Wellness', image: 'rachel' },
  { name: 'Vincenza Visciano', role: 'EmpowHER Women', image: 'vincenza' },
];

export const plans: Plan[] = [
  { name: 'Bronze', price: '$20', summary: 'WhatsApp group, newsletter', benefits: ['Welcome WhatsApp chat group', 'EmpowHER newsletter'] },
  { name: 'Silver', price: '$50', summary: '$25 welcome gift, 10% off events', benefits: ['Welcome coupon or gift, value $25', 'Invitation to the WhatsApp chats', 'Access to merchant list offer', 'Up to 10% off workshops and events'] },
  { name: 'Gold · Biz', price: '$280', summary: 'For women who own a business', benefits: ['Welcome EmpowHER gift set, value $50', 'Feature on the EmpowHER Women bio page', 'One free ¼-space ad in EmpowHER Magazine', 'Up to 15% off workshops and events'] },
];

export const issues: Issue[] = [
  { title: 'EmpowHER Magazine issue 1 cover', image: 'mag1' },
  { title: 'EmpowHER Magazine issue 2 cover', image: 'mag2' },
  { title: 'EmpowHER Magazine issue 3 cover', image: 'mag3' },
];
