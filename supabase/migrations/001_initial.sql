-- Noctem Virtual Dispatcher: Initial Schema
-- Run against your Supabase project's SQL editor

-- ============================================================
-- 1. carrier_profiles — central "source of truth" for each carrier
-- ============================================================
create table if not exists public.carrier_profiles (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null unique references auth.users(id) on delete cascade,
    mc_number   text not null unique,
    dot_number  text,
    legal_name  text,
    dba_name    text,
    allowed_to_operate boolean default false,
    out_of_service     boolean default false,
    safety_rating      text check (safety_rating in ('satisfactory','conditional','unsatisfactory')),
    equipment_types    text[] default '{}',
    preferred_lanes    jsonb  default '[]'::jsonb,
    home_city   text,
    home_state  text,
    telephone   text,
    created_at  timestamptz default now(),
    updated_at  timestamptz default now()
);

create index if not exists idx_carrier_profiles_mc on public.carrier_profiles(mc_number);
create index if not exists idx_carrier_profiles_user on public.carrier_profiles(user_id);

-- Auto-update updated_at on every row change
create or replace function public.set_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

drop trigger if exists trg_carrier_profiles_updated on public.carrier_profiles;
create trigger trg_carrier_profiles_updated
    before update on public.carrier_profiles
    for each row execute function public.set_updated_at();

-- ============================================================
-- 2. loads — mock freight data for MVP, real API later
-- ============================================================
create table if not exists public.loads (
    id              uuid primary key default gen_random_uuid(),
    origin_city     text not null,
    origin_state    text not null,
    origin_lat      double precision,
    origin_lng      double precision,
    dest_city       text not null,
    dest_state      text not null,
    dest_lat        double precision,
    dest_lng        double precision,
    equipment_type  text not null check (equipment_type in ('dry_van','reefer','flatbed','step_deck','tanker')),
    weight_lbs      integer,
    rate_per_mile   numeric(8,2),
    total_rate      numeric(10,2),
    miles           integer,
    pickup_date     date,
    delivery_date   date,
    broker_name     text,
    broker_mc       text,
    status          text default 'available' check (status in ('available','booked','in_transit','delivered')),
    created_at      timestamptz default now()
);

create index if not exists idx_loads_status on public.loads(status);
create index if not exists idx_loads_equipment on public.loads(equipment_type);
create index if not exists idx_loads_origin on public.loads(origin_state);

-- ============================================================
-- 3. market_indices — regional market snapshots
-- ============================================================
create table if not exists public.market_indices (
    id                  uuid primary key default gen_random_uuid(),
    region              text not null,
    lat                 double precision,
    lng                 double precision,
    load_to_truck_ratio numeric(6,2),
    avg_rate_per_mile   numeric(8,2),
    trend               text check (trend in ('up','down','stable')),
    equipment_type      text check (equipment_type in ('dry_van','reefer','flatbed','step_deck','tanker')),
    computed_at         timestamptz default now()
);

create index if not exists idx_market_region on public.market_indices(region);

-- ============================================================
-- 4. call_transcripts — voice agent call logs
-- ============================================================
create table if not exists public.call_transcripts (
    id                uuid primary key default gen_random_uuid(),
    carrier_id        uuid not null references public.carrier_profiles(id) on delete cascade,
    twilio_call_sid   text,
    language_detected text,
    transcript        jsonb default '[]'::jsonb,
    ai_summary        text,
    actions_taken     jsonb default '[]'::jsonb,
    duration_seconds  integer,
    created_at        timestamptz default now()
);

create index if not exists idx_transcripts_carrier on public.call_transcripts(carrier_id);

-- ============================================================
-- 5. Row Level Security
-- ============================================================
alter table public.carrier_profiles enable row level security;
alter table public.loads enable row level security;
alter table public.market_indices enable row level security;
alter table public.call_transcripts enable row level security;

-- carrier_profiles: users can only read/write their own profile
create policy "Users can view own profile"
    on public.carrier_profiles for select
    using (auth.uid() = user_id);

create policy "Users can insert own profile"
    on public.carrier_profiles for insert
    with check (auth.uid() = user_id);

create policy "Users can update own profile"
    on public.carrier_profiles for update
    using (auth.uid() = user_id);

-- loads: all authenticated users can read; only service role can write
create policy "Authenticated users can view loads"
    on public.loads for select
    to authenticated
    using (true);

-- market_indices: all authenticated users can read
create policy "Authenticated users can view market indices"
    on public.market_indices for select
    to authenticated
    using (true);

-- call_transcripts: users see only their own carrier's transcripts
create policy "Users can view own transcripts"
    on public.call_transcripts for select
    using (
        carrier_id in (
            select id from public.carrier_profiles where user_id = auth.uid()
        )
    );

-- Service-role bypass: the backend uses the service_role key, which
-- bypasses RLS automatically, so no extra policies are needed for writes
-- from the FastAPI backend.

-- ============================================================
-- 6. Enable Realtime on carrier_profiles
-- ============================================================
alter publication supabase_realtime add table public.carrier_profiles;
