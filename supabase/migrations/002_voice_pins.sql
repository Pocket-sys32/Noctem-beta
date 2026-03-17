-- Noctem Virtual Dispatcher: Voice PIN linking

create table if not exists public.voice_pins (
    id         uuid primary key default gen_random_uuid(),
    carrier_id uuid not null references public.carrier_profiles(id) on delete cascade,
    pin        text not null,
    expires_at timestamptz not null,
    used_at    timestamptz,
    created_at timestamptz default now()
);

create index if not exists idx_voice_pins_pin on public.voice_pins(pin);
create index if not exists idx_voice_pins_carrier on public.voice_pins(carrier_id);

alter table public.voice_pins enable row level security;

-- Only the owning user can view their pins (optional; primarily accessed via backend service role)
create policy "Users can view own voice pins"
    on public.voice_pins for select
    using (
        carrier_id in (
            select id from public.carrier_profiles where user_id = auth.uid()
        )
    );

-- Backend uses service role and bypasses RLS for inserts/updates.

alter publication supabase_realtime add table public.voice_pins;

