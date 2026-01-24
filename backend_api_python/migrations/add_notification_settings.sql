-- Migration: Add notification_settings column to qd_users table
-- Run this if you see error: column "notification_settings" does not exist

-- Add notification_settings column (if not exists)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'qd_users' AND column_name = 'notification_settings'
    ) THEN
        ALTER TABLE qd_users ADD COLUMN notification_settings TEXT DEFAULT '';
        RAISE NOTICE 'Column notification_settings added to qd_users';
    ELSE
        RAISE NOTICE 'Column notification_settings already exists';
    END IF;
END $$;
