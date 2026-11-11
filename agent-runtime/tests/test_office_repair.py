"""Shared DOCX/PPTX deterministic repair progress, independent of model scores."""
import io
import json
import zipfile
from platform_app import office_repair as policy


def issue(value,evidence=None,key='block'):
    return policy.issue(dict(block=key,code='collision'),evidence or dict(overlap=value),value)


def test_more_than_three_measurable_repairs_can_continue_and_then_pass():
    history=None
    for revision,value in enumerate([.9,.8,.7,.6,.5,.4,.3]):
        history,control=policy.observe(history,[issue(value)],f'content-{revision}',revision)
        assert control['autonomous_repair_allowed'] and control['stop_reason'] is None
        history=json.loads(json.dumps(history))  # A restart retains the evidence.
    history,control=policy.observe(history,[],'fixed',7)
    assert control['status']=='passed' and history['observations']==[]


def test_resolving_a_sequence_of_structural_findings_has_no_round_limit():
    history=None
    for revision,count in enumerate(range(6,0,-1)):
        issues=[policy.issue(dict(code='heading_keep_next',block=str(i))) for i in range(count)]
        history,control=policy.observe(history,issues,str(revision),revision)
        assert control['autonomous_repair_allowed']


def test_repeated_error_stops_even_if_content_and_revision_change():
    history,_=policy.observe(None,[issue(.5)],'before',1)
    history,control=policy.observe(history,[issue(.5)],'changed-unrelated-content',2)
    assert control['stop_reason']=='repeated_errors' and not control['autonomous_repair_allowed']


def test_new_coordinates_without_geometric_improvement_stop():
    history,_=policy.observe(None,[issue(.5,dict(x=1))],'before',1)
    _,control=policy.observe(history,[issue(.6,dict(x=2))],'worse',2)
    assert control['stop_reason']=='no_progress'


def test_oscillation_stops_after_restart():
    history,_=policy.observe(None,[issue(.5)],'A',1)
    history,_=policy.observe(history,[issue(.3)],'B',2)
    _,control=policy.observe(json.loads(json.dumps(history)),[issue(.5)],'A',3)
    assert control['stop_reason']=='repair_cycle'


def test_diagnostic_reads_are_idempotent():
    history,control=policy.observe(None,[issue(.5)],'same',1)
    updated,repeated=policy.observe(history,[issue(.5)],'same',1)
    assert updated==history and repeated==control


def test_zip_timestamps_do_not_count_as_content_progress():
    def package(year):
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as archive:
            archive.writestr(zipfile.ZipInfo('word/document.xml',(year,1,1,0,0,0)),b'<document/>')
        return stream.getvalue()
    before,after=package(2025),package(2026)
    assert before!=after
    assert policy.package_fingerprint(before)==policy.package_fingerprint(after)


def test_multiple_findings_for_one_block_measure_the_entire_defect():
    history,_=policy.observe(None,[issue(.2),issue(.3)],'A',1)
    # One smaller sub-overlap cannot hide a much larger unresolved collision.
    _,control=policy.observe(history,[issue(.1),issue(.6)],'B',2)
    assert control['stop_reason']=='no_progress'
