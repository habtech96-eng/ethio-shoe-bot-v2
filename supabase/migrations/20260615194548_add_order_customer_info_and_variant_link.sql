-- Add missing customer info columns to orders
ALTER TABLE public.orders 
ADD COLUMN IF NOT EXISTS customer_name TEXT,
ADD COLUMN IF NOT EXISTS customer_phone TEXT;

-- Add variant_id to order_items for stock tracking
ALTER TABLE public.order_items 
ADD COLUMN IF NOT EXISTS variant_id UUID REFERENCES public.product_variants(id) ON DELETE SET NULL;

-- Create index for the new column
CREATE INDEX IF NOT EXISTS idx_order_items_variant_id ON public.order_items(variant_id);