"""Evidence-bound technical and editorial review. Never an automatic ROI certificate."""
import math

from .campaign import check_campaign, text, concept_mode, real_reference
from .core import digest, sha
from .validation import require

CHECKS = ['hook', 'proof', 'purchase_reason', 'visual_identity', 'claims', 'text', 'audio', 'continuity', 'cta']


def review_template(ws, story_file, inspection_file):
    story, report = ws.load(story_file), ws.load(inspection_file)
    check_campaign(story, ws)
    require(isinstance(report, dict), 'Inspection must be an object')
    checks = CHECKS + (['disclosure'] if concept_mode(story) else [])
    return {'version': 1, 'story_digest': digest(story), 'story_sha256': sha(ws.input_path(story_file)),
            'inspection_sha256': sha(ws.input_path(inspection_file)), 'media_sha256': report['media_sha256'],
            'reviewer': '', 'review_type': 'editorial_assessment', 'full_video_watched': False,
            'audio_listened': False, 'shots_reviewed': [],
            'checks': [{'id': c, 'status': 'UNKNOWN', 'observations': []} for c in checks],
            'instruction': 'Watch the entire exact final file, listen when audio required; record observed shot/time and what supports each verdict. Frame sampling is not full viewing. Do not fill PASS from the script alone.'}


def accept_campaign(ws, story_file, inspection_file, review):
    story, report = ws.load(story_file), ws.load(inspection_file)
    check_campaign(story, ws)
    require(isinstance(review, dict) and isinstance(report, dict), 'Review and inspection must be JSON objects')
    require(review.get('story_digest') == digest(story) and review.get('story_sha256') == sha(ws.input_path(story_file)), 'Storyboard changed after review')
    require(review.get('inspection_sha256') == sha(ws.input_path(inspection_file)), 'Inspection changed after review')
    require(review.get('media_sha256') == report['media_sha256'] == sha(ws.input_path(report['media'])), 'Reviewed media changed')
    for artifact in report.get('frames', []) + ([report['audio']] if report.get('audio') else []):
        require(sha(ws.input_path(artifact['path'])) == artifact['sha256'], 'Review evidence changed')
    delivery = story['delivery']
    a, b = map(int, story['ratio'].split(':'))

    def number(value):
        return type(value) in (float, int) and math.isfinite(value)

    duration, ratio = report.get('duration'), report.get('display_ratio')
    technical = {'full_decode': report.get('full_decode') is True,
        'duration': number(duration) and abs(duration - delivery['duration']) <= delivery['duration_tolerance'],
        'ratio': number(ratio) and abs(ratio / (a / b) - 1) <= delivery['ratio_tolerance'],
        'size': all(number(report.get(k)) and report[k] >= delivery['min_short_side'] for k in ('width', 'height')),
        'audio_track': delivery['audio'] == 'silent' or report.get('audio_tracks', 0) > 0,
        'video_coverage': all(number(report.get(k)) for k in ('video_start', 'video_end', 'max_video_gap')) and
            report['video_start'] <= 0.05 and report['video_end'] >= delivery['duration'] - delivery['duration_tolerance'] and report['max_video_gap'] <= 0.1}
    issues = ['technical:' + key for key, passed in technical.items() if not passed]
    if not concept_mode(story) and not real_reference(story):
        issues.append('real_product_reference_missing')
    if review.get('full_video_watched') is not True:
        issues.append('full_video_not_watched')
    if delivery['audio'] == 'required' and review.get('audio_listened') is not True:
        issues.append('audio_not_listened')
    if not text(review.get('reviewer')):
        issues.append('reviewer_missing')
    shot_ids = {s['id'] for s in story['shots']}
    require(isinstance(review.get('shots_reviewed', []), list) and all(text(s) for s in review.get('shots_reviewed', [])), 'shots_reviewed must be a string list')
    if set(review.get('shots_reviewed', [])) != shot_ids:
        issues.append('not_all_shots_reviewed')
    expected = CHECKS + (['disclosure'] if concept_mode(story) else [])
    checks = review.get('checks', [])
    require(isinstance(checks, list) and all(isinstance(c, dict) for c in checks), 'Review checks must be objects')
    ids = [c.get('id') for c in checks]
    require(len(ids) == len(set(ids)) and set(ids) == set(expected), 'Complete exactly the required editorial checks')
    revisions, observed_shots, bounds, offset = set(), set(), {}, 0
    for shot in story['shots']:
        bounds[shot['id']] = (offset, offset + shot['duration'])
        offset += shot['duration']
    for check in checks:
        observations = check.get('observations', [])
        require(isinstance(observations, list), 'Observations must be a list')
        valid_observations = bool(observations)
        for obs in observations:
            valid = isinstance(obs, dict) and obs.get('shot') in shot_ids and number(obs.get('seconds')) and 0 <= obs['seconds'] <= report['duration'] and text(obs.get('note'))
            require(valid, 'Each observation needs a real shot id, bounded timestamp and concrete note')
            start, end = bounds[obs['shot']]
            require(start <= obs['seconds'] <= end, 'Observation timestamp does not belong to the named shot')
            observed_shots.add(obs['shot'])
        if check.get('status') != 'PASS' or not valid_observations:
            issues.append('editorial:' + check['id'])
            revisions.update(obs['shot'] for obs in observations)
    if observed_shots != shot_ids:
        issues.append('shots_without_observations')
    accepted = not issues
    fictional = concept_mode(story)
    return {'accepted': accepted,
        'state': ('concept_content_review_passed' if fictional else 'content_review_passed') if accepted else 'needs_review_or_revision',
        'technical': technical, 'issues': issues, 'revision_shots': sorted(revisions),
        'next_action': 'Deliver the reviewed concept; publishing needs separate authorization' if accepted else 'Inspect the failed checks; edit only affected shots and obtain a new concrete budget before any paid regeneration',
        'story_digest': digest(story), 'media_sha256': report['media_sha256'], 'review_digest': digest(review),
        'real_product_fidelity_verified': False, 'sales_effect': 'NOT_RUN',
        'review_limit': 'Editorial assessment supplied by the named reviewer, not independent fact or sales verification',
        'external_calls': 0}
