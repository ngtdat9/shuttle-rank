# Shuttle Rank frontend

Next.js app for the club ranking site. Dark design system, public pages, and a later admin UI.

```bash
npm install
npm run dev
```

Copy `.env.example` to `.env.local` when you need local overrides. Placeholders only — never put the Supabase service-role key in `NEXT_PUBLIC_*`.

```bash
npm run lint
npx tsc --noEmit
npm run build
npm run format
```

`/design` is a component showcase and is not linked from the navigation.
