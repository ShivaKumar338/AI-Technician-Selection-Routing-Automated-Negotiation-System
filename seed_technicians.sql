-- Realistic technician seed data for Hyderabad
-- Run in Supabase → SQL Editor → Run

-- Clear old seed data first (optional — comment out if you want to keep existing)
-- DELETE FROM technicians WHERE name IN ('Ravi Reddy','Suresh Rao','Kiran Kumar');

INSERT INTO technicians (id, name, skills, lat, lng, rate_min, rating, available, phone_number)
VALUES
  (gen_random_uuid(), 'Arjun Reddy',     ARRAY['AC','electrical'],          17.4156, 78.4347, 400, 4.8, true,  '9603831929'),
  (gen_random_uuid(), 'Suresh Naidu',    ARRAY['plumbing','appliance'],     17.3850, 78.4867, 350, 4.5, true,  '8520929979'),
  (gen_random_uuid(), 'Vikram Sharma',   ARRAY['AC','appliance'],           17.4400, 78.3800, 500, 4.9, true,  '9603831929'),
  (gen_random_uuid(), 'Kiran Rao',       ARRAY['electrical','carpentry'],   17.3600, 78.5100, 300, 4.2, true,  '8520929979'),
  (gen_random_uuid(), 'Prasad Varma',    ARRAY['plumbing'],                 17.4700, 78.4200, 280, 4.0, false, '9603831929'),
  (gen_random_uuid(), 'Naveen Gupta',    ARRAY['AC','plumbing','electrical'],17.3950, 78.4650, 550, 4.7, true,  '8520929979'),
  (gen_random_uuid(), 'Mahesh Iyer',     ARRAY['carpentry','painting'],     17.4250, 78.5300, 320, 4.3, true,  '9603831929'),
  (gen_random_uuid(), 'Rajesh Chowdary', ARRAY['electrical'],               17.3750, 78.4100, 380, 4.6, true,  '8520929979'),
  (gen_random_uuid(), 'Srinivas Babu',   ARRAY['AC'],                       17.4500, 78.4900, 450, 4.4, true,  '9603831929'),
  (gen_random_uuid(), 'Gopal Murthy',    ARRAY['plumbing','carpentry'],     17.3300, 78.5500, 290, 3.9, false, '8520929979'),
  (gen_random_uuid(), 'Deepak Pillai',   ARRAY['appliance','electrical'],   17.4050, 78.3600, 420, 4.5, true,  '9603831929'),
  (gen_random_uuid(), 'Sanjay Yadav',    ARRAY['painting','carpentry'],     17.3450, 78.4750, 260, 4.1, true,  '8520929979'),
  (gen_random_uuid(), 'Ramesh Acharya',  ARRAY['AC','plumbing'],            17.4600, 78.5000, 480, 4.8, true,  '9603831929'),
  (gen_random_uuid(), 'Ajay Goud',       ARRAY['electrical','appliance'],   17.3850, 78.3900, 360, 4.3, true,  '8520929979'),
  (gen_random_uuid(), 'Karthik Mohan',   ARRAY['AC','electrical','painting'],17.4300, 78.4600, 520, 4.9, true,  '9603831929')
ON CONFLICT DO NOTHING;

-- Update phone numbers on existing technicians that have none
UPDATE technicians
SET phone_number = CASE
    WHEN (ROW_NUMBER() OVER (ORDER BY id)) % 2 = 0 THEN '8520929979'
    ELSE '9603831929'
END
WHERE phone_number IS NULL;
