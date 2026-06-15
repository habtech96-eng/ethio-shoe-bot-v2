-- Create product-images storage bucket for Supabase Storage
-- Note: Storage buckets are created via the Supabase dashboard or API
-- This migration documents the expected bucket configuration

COMMENT ON SCHEMA public IS 'Ethio Shoe Store - Production Schema with Storage';

-- Create a table to track storage bucket metadata (optional, for documentation)
CREATE TABLE IF NOT EXISTS public.storage_buckets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    public BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert bucket record
INSERT INTO public.storage_buckets (id, name, public) 
VALUES ('product-images', 'product-images', TRUE)
ON CONFLICT (id) DO NOTHING;

-- Storage policies are managed via Supabase Dashboard
-- Bucket 'product-images' should have:
-- 1. Public: true (for public URL access)
-- 2. Allowed MIME types: image/*
-- 3. Max file size: 5MB

COMMENT ON TABLE public.storage_buckets IS 'Metadata for Supabase Storage buckets used by the application';