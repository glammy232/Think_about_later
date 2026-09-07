CREATE SEQUENCE "public"."direct_debts_id_seq" AS bigint INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START WITH 1 CACHE 1 NO CYCLE;

CREATE SEQUENCE "public"."incomes_id_seq" AS bigint INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START WITH 1 CACHE 1 NO CYCLE;

CREATE TABLE "public"."direct_debts" (
  "id"          bigint                   NOT NULL DEFAULT nextval('public.direct_debts_id_seq'::regclass),
  "group_id"    integer                  NOT NULL,
  "debtor_id"   integer                  NOT NULL,
  "creditor_id" integer                  NOT NULL,
  "amount"      numeric(12,2)            NOT NULL,
  "description" text                     NOT NULL,
  "status"      text                     NOT NULL DEFAULT 'active'::text,
  "due_date"    date,
  "created_at"  timestamp with time zone NOT NULL DEFAULT now(),
  "settled_at"  timestamp with time zone,
  CONSTRAINT "direct_debts_amount_check" CHECK ((amount > (0)::numeric)),
  CONSTRAINT "direct_debts_check" CHECK ((debtor_id <> creditor_id)),
  CONSTRAINT "direct_debts_pkey" PRIMARY KEY (id),
  CONSTRAINT "direct_debts_status_check" CHECK ((status = ANY (ARRAY['active'::text, 'settled'::text])))
);

CREATE TABLE "public"."incomes" (
  "id"          bigint                   NOT NULL DEFAULT nextval('public.incomes_id_seq'::regclass),
  "group_id"    integer                  NOT NULL,
  "received_by" integer                  NOT NULL,
  "title"       text                     NOT NULL,
  "category"    text                     NOT NULL,
  "amount"      numeric(12,2)            NOT NULL,
  "income_date" date                     NOT NULL,
  "comment"     text,
  "source"      text                     NOT NULL DEFAULT 'manual'::text,
  "created_at"  timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT "incomes_amount_check" CHECK ((amount > (0)::numeric)),
  CONSTRAINT "incomes_pkey" PRIMARY KEY (id)
);

ALTER SEQUENCE "public"."direct_debts_id_seq" OWNED BY "public"."direct_debts"."id";

ALTER TABLE "public"."expenses"
  ADD COLUMN "title" text;

ALTER TABLE "public"."expenses"
  ADD COLUMN "split_type" text NOT NULL DEFAULT 'equal'::text;

ALTER TABLE "public"."expenses"
  ADD COLUMN "comment" text;

ALTER TABLE "public"."expenses"
  ADD COLUMN "source" text NOT NULL DEFAULT 'manual'::text;

ALTER SEQUENCE "public"."incomes_id_seq" OWNED BY "public"."incomes"."id";

ALTER TABLE "public"."settlements"
  ADD COLUMN "comment" text;

ALTER TABLE "public"."direct_debts"
  ADD CONSTRAINT "direct_debts_creditor_id_fkey" FOREIGN KEY (creditor_id) REFERENCES public.users(id) ON DELETE RESTRICT;

ALTER TABLE "public"."direct_debts"
  ADD CONSTRAINT "direct_debts_debtor_id_fkey" FOREIGN KEY (debtor_id) REFERENCES public.users(id) ON DELETE RESTRICT;

ALTER TABLE "public"."direct_debts"
  ADD CONSTRAINT "direct_debts_group_id_fkey" FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE CASCADE;

ALTER TABLE "public"."expenses"
  ADD CONSTRAINT "expenses_split_type_check" CHECK ((split_type = ANY (ARRAY['equal'::text, 'custom'::text, 'percentage'::text])));

ALTER TABLE "public"."incomes"
  ADD CONSTRAINT "incomes_group_id_fkey" FOREIGN KEY (group_id) REFERENCES public.groups(id) ON DELETE CASCADE;

ALTER TABLE "public"."incomes"
  ADD CONSTRAINT "incomes_received_by_fkey" FOREIGN KEY (received_by) REFERENCES public.users(id) ON DELETE RESTRICT;

CREATE INDEX idx_direct_debts_group_status ON public.direct_debts USING btree (group_id, status);

CREATE INDEX idx_incomes_group_date ON public.incomes USING btree (group_id, income_date DESC);

GRANT SELECT, UPDATE, USAGE ON SEQUENCE "public"."direct_debts_id_seq" TO "anon", "authenticated", "postgres", "service_role";

GRANT SELECT, UPDATE, USAGE ON SEQUENCE "public"."incomes_id_seq" TO "anon", "authenticated", "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."direct_debts" TO "anon", "authenticated", "postgres", "service_role";

GRANT DELETE, INSERT, MAINTAIN, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE ON TABLE "public"."incomes" TO "anon", "authenticated", "postgres", "service_role";
