from __future__ import annotations

import copy
import sqlite3
import unittest
from contextlib import closing

from test_modules import FeatureCase
from test_v1_matching import policy
from kho_tri_thuc.ha_tang.database import migrate
from kho_tri_thuc.ha_tang.primitives import DataError
from kho_tri_thuc.ha_tang.runtime import transaction
from kho_tri_thuc.kiem_chung.fixtures import KNOWN, CUTOFF, REVIEW_AT
from kho_tri_thuc.kiem_chung.fixtures import knowledge_fixture
from kho_tri_thuc.ha_tang.runtime import document, source_bundle
from kho_tri_thuc.de_xuat.engine import Engine
from kho_tri_thuc.tri_thuc.service import Knowledge
from kho_tri_thuc.tri_thuc.expiry import configured_valid_to
from kho_tri_thuc.tri_thuc.matching import literal_pattern, compile_pattern


class V1bTests(FeatureCase):
    def test_key_fallback_matches_even_when_description_contains_keyword(self):
        p=policy()
        attempt,banks,_=self.seed(knowledge=knowledge_fixture()[:-1]+[p])
        bank={**document(self.store,banks[0]),'description':'MUA HOA CHAT PHI'}
        result=Engine(self.store).preview(bank,source_bundle(self.store,attempt,CUTOFF),CUTOFF)
        self.assertEqual(result['completeness'],'FULL')

    def test_tier_five_requires_identity_and_does_not_guess_counterparty(self):
        p=policy(tier=5,trigger={'mode':'REGEX','regex':r'\bTHANH TOAN\b'})
        p['payload']['fields']['counterparty']=None
        attempt,banks,_=self.seed(knowledge=knowledge_fixture()[:-1]+[p])
        bank=document(self.store,banks[0])
        engine=Engine(self.store)
        bundle=source_bundle(self.store,attempt,CUTOFF)
        known=engine.preview(bank,bundle,CUTOFF)
        self.assertEqual(known['completeness'],'FULL')
        self.assertNotIn('TEMPLATE_IDENTIFIER_CONFLICT',known['constraints'])
        unknown=engine.preview({**bank,'counterparty_account':None},bundle,CUTOFF)
        self.assertEqual(unknown['completeness'],'PARTIAL')
        self.assertIsNone(unknown['fields']['counterparty'])

    def test_cache_matches_uncached_across_dates_categories_cutoffs(self):
        first = policy()
        first['valid_to'] = '2026-09-10'
        second = policy('later',order=2)
        second['valid_from'] = '2026-09-10'
        for item in [first,second]:
            key=self.kb.stage_many([item],'TEST',KNOWN)[0]
            self.kb.approve(key,'TEST',KNOWN)
        plain=Knowledge(self.store,cache_enabled=False)
        for day in ('2026-09-01','2026-09-10','2026-09-20'):
            for cutoff in (KNOWN,CUTOFF,REVIEW_AT):
                for category in (None,'POLICY','CASE','CATALOG'):
                    self.assertEqual(self.kb.query(day,cutoff,category),plain.query(day,cutoff,category))
                self.assertEqual(self.kb.expired(day,cutoff),plain.expired(day,cutoff))

    def test_full_proposal_is_identical_with_cache_disabled(self):
        attempt,banks,_=self.seed()
        cached,plain=Engine(self.store),Engine(self.store)
        plain.knowledge=Knowledge(self.store,cache_enabled=False)
        bundle=source_bundle(self.store,attempt,CUTOFF)
        for key in banks:
            bank=document(self.store,key)
            for baseline in ('A','B'):
                self.assertEqual(cached.preview(bank,bundle,CUTOFF,baseline),plain.preview(bank,bundle,CUTOFF,baseline))

    def test_other_instance_approval_and_revoke_invalidate(self):
        key=self.kb.stage_many([policy()],'TEST',KNOWN)[0]
        other=Knowledge(self.store)
        self.assertEqual(self.kb.query('2026-09-10',CUTOFF),[])
        other.approve(key,'TEST',KNOWN)
        self.assertEqual(len(self.kb.query('2026-09-10',CUTOFF)),1)
        other.revoke(key,'TEST',KNOWN,'test')
        self.assertEqual(self.kb.query('2026-09-10',CUTOFF),[])

    def test_other_connection_invalidation(self):
        key=self.kb.stage_many([policy()],'TEST',KNOWN)[0]
        self.assertEqual(self.kb.query('2026-09-10',CUTOFF),[])
        db_path=self.store.conn.execute('PRAGMA database_list').fetchone()[2]
        with closing(sqlite3.connect(db_path)) as other:
            other.execute("INSERT INTO knowledge_events(version_id,action,event_at,actor,reason) VALUES (?,'APPROVE',?,'TEST','test')",(key,KNOWN))
            other.commit()
        self.assertEqual(len(self.kb.query('2026-09-10',CUTOFF)),1)

    def test_cache_cannot_be_mutated_by_caller(self):
        key=self.kb.stage_many([policy()],'TEST',KNOWN)[0]
        self.kb.approve(key,'TEST',KNOWN)
        rows=self.kb.query('2026-09-10',CUTOFF)
        rows[0]['payload']['fields']['counterparty']='tampered'
        self.assertNotEqual(self.kb.query('2026-09-10',CUTOFF)[0]['payload']['fields']['counterparty'],'tampered')

    def test_rollback_restores_cache_epoch(self):
        key=self.kb.stage_many([policy()],'TEST',KNOWN)[0]
        self.assertEqual(self.kb.query('2026-09-10',CUTOFF),[])
        with self.assertRaises(RuntimeError):
            with transaction(self.store):
                self.store.conn.execute("INSERT INTO knowledge_events(version_id,action,event_at,actor,reason) VALUES (?,'APPROVE',?,'TEST','test')",(key,KNOWN))
                self.assertEqual(len(self.kb.query('2026-09-10',CUTOFF)),1)
                raise RuntimeError('rollback')
        self.assertEqual(self.kb.query('2026-09-10',CUTOFF),[])

    def test_configured_expiry_keeps_raw_and_checks_derived_date(self):
        p=policy(expiry_raw='2026-01-01',expiry_policy={'mode':'LAST_SEEN_DAYS','days':365,'last_seen':'2026-01-01'})
        p['valid_to']='2027-01-02'
        self.kb.stage_many([p],'TEST',KNOWN)
        p['valid_to']='2026-01-02'
        with self.assertRaises(DataError):self.kb.stage_many([p],'TEST',KNOWN)
        self.assertEqual(configured_valid_to({'expiry_policy':{'mode':'LAST_SEEN_DAYS','days':180,'last_seen':'2026-01-01'}}),'2026-07-01')

    def test_rollback_followed_by_other_event_cannot_reuse_cached_generation(self):
        first,second=self.kb.stage_many([policy(),policy('second',order=2)],'TEST',KNOWN)
        with self.assertRaises(RuntimeError):
            with transaction(self.store):
                self.store.conn.execute("INSERT INTO knowledge_events(version_id,action,event_at,actor,reason) VALUES (?,'APPROVE',?,'TEST','test')",(first,KNOWN))
                self.assertEqual(self.kb.query('2026-09-10',CUTOFF)[0]['id'],first)
                raise RuntimeError('rollback')
        Knowledge(self.store).approve(second,'TEST',KNOWN)
        self.assertEqual([x['id'] for x in self.kb.query('2026-09-10',CUTOFF)],[second])

    def test_unlimited_expiry_only_verified_identifier(self):
        payload={'kind':'IDENTIFIER','verified':True,'expiry_policy':{'mode':'VERIFIED_IDENTIFIER_NO_EXPIRY'}}
        self.assertIsNone(configured_valid_to(payload))
        payload['verified']=False
        with self.assertRaises(DataError):configured_valid_to(payload)

    def test_generic_regex_builder_has_no_business_exclusion(self):
        self.assertIsNotNone(compile_pattern(literal_pattern('MUA HOA')).search('MUA HOA CHAT'))

    def test_stage_query_uses_rank_index(self):
        plan=self.store.conn.execute("""EXPLAIN QUERY PLAN SELECT valid_from,valid_to FROM knowledge_versions
            WHERE category='POLICY' AND json_extract(payload_json,'$.contract_version')=2
            AND json_extract(payload_json,'$.partition')=? AND json_extract(payload_json,'$.tier')=?
            AND json_extract(payload_json,'$.order')=? AND logical_key<>?""",('TEST',1,1,'key')).fetchall()
        self.assertIn('knowledge_policy_rank',' '.join(str(tuple(r)) for r in plan))

    def test_migration_v8_to_v9_preserves_history(self):
        with sqlite3.connect(':memory:',isolation_level=None) as conn:
            migrate(conn,8)
            before=list(conn.execute('SELECT version,checksum FROM schema_migrations'))
            migrate(conn)
            self.assertEqual(before,list(conn.execute('SELECT version,checksum FROM schema_migrations WHERE version<=8')))
            self.assertGreaterEqual(conn.execute('PRAGMA user_version').fetchone()[0],9)
            self.assertEqual(conn.execute('PRAGMA integrity_check').fetchone()[0],'ok')


if __name__=='__main__':unittest.main()
