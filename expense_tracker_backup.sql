--
-- PostgreSQL database dump
--

-- Dumped from database version 17.6
-- Dumped by pg_dump version 17.5

-- Started on 2025-08-30 23:16:11

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 224 (class 1259 OID 24612)
-- Name: balance; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.balance (
    id integer NOT NULL,
    user_id integer NOT NULL,
    amount double precision NOT NULL,
    last_updated timestamp without time zone NOT NULL
);


ALTER TABLE public.balance OWNER TO postgres;

--
-- TOC entry 223 (class 1259 OID 24611)
-- Name: balance_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.balance_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.balance_id_seq OWNER TO postgres;

--
-- TOC entry 4958 (class 0 OID 0)
-- Dependencies: 223
-- Name: balance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.balance_id_seq OWNED BY public.balance.id;


--
-- TOC entry 220 (class 1259 OID 24586)
-- Name: category; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.category (
    id integer NOT NULL,
    name character varying(50) NOT NULL
);


ALTER TABLE public.category OWNER TO postgres;

--
-- TOC entry 219 (class 1259 OID 24585)
-- Name: category_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.category_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.category_id_seq OWNER TO postgres;

--
-- TOC entry 4959 (class 0 OID 0)
-- Dependencies: 219
-- Name: category_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.category_id_seq OWNED BY public.category.id;


--
-- TOC entry 222 (class 1259 OID 24595)
-- Name: expense; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.expense (
    id integer NOT NULL,
    amount double precision NOT NULL,
    category_id integer NOT NULL,
    category_description character varying(255),
    user_id integer NOT NULL,
    date date NOT NULL,
    split_type character varying(20) NOT NULL
);


ALTER TABLE public.expense OWNER TO postgres;

--
-- TOC entry 221 (class 1259 OID 24594)
-- Name: expense_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.expense_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.expense_id_seq OWNER TO postgres;

--
-- TOC entry 4960 (class 0 OID 0)
-- Dependencies: 221
-- Name: expense_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.expense_id_seq OWNED BY public.expense.id;


--
-- TOC entry 226 (class 1259 OID 24624)
-- Name: expense_participant; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.expense_participant (
    id integer NOT NULL,
    expense_id integer NOT NULL,
    user_id integer NOT NULL,
    amount_owed double precision NOT NULL
);


ALTER TABLE public.expense_participant OWNER TO postgres;

--
-- TOC entry 225 (class 1259 OID 24623)
-- Name: expense_participant_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.expense_participant_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.expense_participant_id_seq OWNER TO postgres;

--
-- TOC entry 4961 (class 0 OID 0)
-- Dependencies: 225
-- Name: expense_participant_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.expense_participant_id_seq OWNED BY public.expense_participant.id;


--
-- TOC entry 228 (class 1259 OID 32769)
-- Name: settlement; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.settlement (
    id integer NOT NULL,
    amount double precision NOT NULL,
    payer_id integer NOT NULL,
    receiver_id integer NOT NULL,
    date date NOT NULL,
    description character varying(255),
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.settlement OWNER TO postgres;

--
-- TOC entry 227 (class 1259 OID 32768)
-- Name: settlement_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.settlement_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.settlement_id_seq OWNER TO postgres;

--
-- TOC entry 4962 (class 0 OID 0)
-- Dependencies: 227
-- Name: settlement_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.settlement_id_seq OWNED BY public.settlement.id;


--
-- TOC entry 218 (class 1259 OID 24577)
-- Name: user; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public."user" (
    id integer NOT NULL,
    name character varying(50) NOT NULL
);


ALTER TABLE public."user" OWNER TO postgres;

--
-- TOC entry 217 (class 1259 OID 24576)
-- Name: user_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_id_seq OWNER TO postgres;

--
-- TOC entry 4963 (class 0 OID 0)
-- Dependencies: 217
-- Name: user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.user_id_seq OWNED BY public."user".id;


--
-- TOC entry 4770 (class 2604 OID 24615)
-- Name: balance id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.balance ALTER COLUMN id SET DEFAULT nextval('public.balance_id_seq'::regclass);


--
-- TOC entry 4768 (class 2604 OID 24589)
-- Name: category id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.category ALTER COLUMN id SET DEFAULT nextval('public.category_id_seq'::regclass);


--
-- TOC entry 4769 (class 2604 OID 24598)
-- Name: expense id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.expense ALTER COLUMN id SET DEFAULT nextval('public.expense_id_seq'::regclass);


--
-- TOC entry 4771 (class 2604 OID 24627)
-- Name: expense_participant id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.expense_participant ALTER COLUMN id SET DEFAULT nextval('public.expense_participant_id_seq'::regclass);


--
-- TOC entry 4772 (class 2604 OID 32772)
-- Name: settlement id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.settlement ALTER COLUMN id SET DEFAULT nextval('public.settlement_id_seq'::regclass);


--
-- TOC entry 4767 (class 2604 OID 24580)
-- Name: user id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."user" ALTER COLUMN id SET DEFAULT nextval('public.user_id_seq'::regclass);


--
-- TOC entry 4948 (class 0 OID 24612)
-- Dependencies: 224
-- Data for Name: balance; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.balance (id, user_id, amount, last_updated) FROM stdin;
3896	8	-1190.6000000000001	2025-08-31 03:45:17.622904
3895	7	-1.1368683772161603e-13	2025-08-31 03:45:17.627144
3894	5	0	2025-08-31 03:45:17.632651
3893	6	-295.8000000000001	2025-08-31 03:45:17.63448
3897	9	1486.4000000000008	2025-08-31 03:45:17.6356
\.


--
-- TOC entry 4944 (class 0 OID 24586)
-- Dependencies: 220
-- Data for Name: category; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.category (id, name) FROM stdin;
1	Groceries
7	Rent
15	Utilities
\.


--
-- TOC entry 4946 (class 0 OID 24595)
-- Dependencies: 222
-- Data for Name: expense; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.expense (id, amount, category_id, category_description, user_id, date, split_type) FROM stdin;
59	102	1	Costco	6	2025-08-19	equal
60	30	1	Walmart	6	2025-08-19	equal
63	190	1	Costco	5	2025-08-22	equal
61	2375	7	August- Prorated	9	2025-08-09	equal
64	3200	7	September	9	2025-09-03	equal
62	56	1	Jewel	5	2025-08-22	equal
\.


--
-- TOC entry 4950 (class 0 OID 24624)
-- Dependencies: 226
-- Data for Name: expense_participant; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.expense_participant (id, expense_id, user_id, amount_owed) FROM stdin;
215	60	5	6
216	60	6	6
217	60	7	6
218	60	8	6
219	60	9	6
220	61	5	475
221	61	6	475
222	61	7	475
223	61	8	475
224	61	9	475
230	63	5	38
231	63	6	38
232	63	7	38
233	63	8	38
234	63	9	38
235	64	5	640
210	59	5	20.4
236	64	6	640
237	64	7	640
238	64	8	640
211	59	6	20.4
212	59	7	20.4
213	59	8	20.4
214	59	9	20.4
239	64	9	640
225	62	5	11.2
226	62	6	11.2
227	62	7	11.2
228	62	8	11.2
229	62	9	11.2
\.


--
-- TOC entry 4952 (class 0 OID 32769)
-- Dependencies: 228
-- Data for Name: settlement; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.settlement (id, amount, payer_id, receiver_id, date, description, created_at) FROM stdin;
29	475	7	9	2025-08-09	\N	2025-08-31 01:42:22.387847
30	715.6	7	9	2025-08-30	\N	2025-08-31 01:43:36.565443
31	469.6	5	9	2025-08-30	\N	2025-08-31 01:45:54.118279
27	475	6	9	2025-08-09	\N	2025-08-31 01:40:49.015554
28	475	5	9	2025-08-09	\N	2025-08-31 01:41:40.991945
37	287.8	6	9	2025-08-30	\N	2025-08-31 03:42:11.119723
\.


--
-- TOC entry 4942 (class 0 OID 24577)
-- Dependencies: 218
-- Data for Name: user; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public."user" (id, name) FROM stdin;
5	Zach
6	Jake
7	Nick
8	Aaron
9	Jakub
\.


--
-- TOC entry 4964 (class 0 OID 0)
-- Dependencies: 223
-- Name: balance_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.balance_id_seq', 3897, true);


--
-- TOC entry 4965 (class 0 OID 0)
-- Dependencies: 219
-- Name: category_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.category_id_seq', 15, true);


--
-- TOC entry 4966 (class 0 OID 0)
-- Dependencies: 221
-- Name: expense_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.expense_id_seq', 65, true);


--
-- TOC entry 4967 (class 0 OID 0)
-- Dependencies: 225
-- Name: expense_participant_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.expense_participant_id_seq', 244, true);


--
-- TOC entry 4968 (class 0 OID 0)
-- Dependencies: 227
-- Name: settlement_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.settlement_id_seq', 37, true);


--
-- TOC entry 4969 (class 0 OID 0)
-- Dependencies: 217
-- Name: user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.user_id_seq', 12, true);


--
-- TOC entry 4784 (class 2606 OID 24617)
-- Name: balance balance_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.balance
    ADD CONSTRAINT balance_pkey PRIMARY KEY (id);


--
-- TOC entry 4778 (class 2606 OID 24593)
-- Name: category category_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.category
    ADD CONSTRAINT category_name_key UNIQUE (name);


--
-- TOC entry 4780 (class 2606 OID 24591)
-- Name: category category_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.category
    ADD CONSTRAINT category_pkey PRIMARY KEY (id);


--
-- TOC entry 4786 (class 2606 OID 24629)
-- Name: expense_participant expense_participant_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.expense_participant
    ADD CONSTRAINT expense_participant_pkey PRIMARY KEY (id);


--
-- TOC entry 4782 (class 2606 OID 24600)
-- Name: expense expense_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.expense
    ADD CONSTRAINT expense_pkey PRIMARY KEY (id);


--
-- TOC entry 4788 (class 2606 OID 32774)
-- Name: settlement settlement_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.settlement
    ADD CONSTRAINT settlement_pkey PRIMARY KEY (id);


--
-- TOC entry 4774 (class 2606 OID 24584)
-- Name: user user_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_name_key UNIQUE (name);


--
-- TOC entry 4776 (class 2606 OID 24582)
-- Name: user user_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);


--
-- TOC entry 4791 (class 2606 OID 24618)
-- Name: balance balance_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.balance
    ADD CONSTRAINT balance_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- TOC entry 4789 (class 2606 OID 24601)
-- Name: expense expense_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.expense
    ADD CONSTRAINT expense_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.category(id);


--
-- TOC entry 4792 (class 2606 OID 24630)
-- Name: expense_participant expense_participant_expense_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.expense_participant
    ADD CONSTRAINT expense_participant_expense_id_fkey FOREIGN KEY (expense_id) REFERENCES public.expense(id);


--
-- TOC entry 4793 (class 2606 OID 24635)
-- Name: expense_participant expense_participant_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.expense_participant
    ADD CONSTRAINT expense_participant_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- TOC entry 4790 (class 2606 OID 24606)
-- Name: expense expense_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.expense
    ADD CONSTRAINT expense_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- TOC entry 4794 (class 2606 OID 32775)
-- Name: settlement settlement_payer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.settlement
    ADD CONSTRAINT settlement_payer_id_fkey FOREIGN KEY (payer_id) REFERENCES public."user"(id);


--
-- TOC entry 4795 (class 2606 OID 32780)
-- Name: settlement settlement_receiver_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.settlement
    ADD CONSTRAINT settlement_receiver_id_fkey FOREIGN KEY (receiver_id) REFERENCES public."user"(id);


-- Completed on 2025-08-30 23:16:12

--
-- PostgreSQL database dump complete
--

