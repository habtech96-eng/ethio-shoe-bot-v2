ALTER TABLE public.product_variants
ADD COLUMN IF NOT EXISTS telegram_file_id text;
