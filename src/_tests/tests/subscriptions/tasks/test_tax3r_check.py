from pytest_mock import MockFixture, MockType

import json
import uuid

from apps.subscriptions.models.payments import Payment
from apps.subscriptions.services.tax3r_check_processor import Tax3rCheckProcessor
from apps.subscriptions.tasks.tax3r_check import Tax3rCheckProcessorTaskService, process_tax3r_check_results


def _make_raw(
    success: bool = True,
    link: str = 'https://tax3r.example.com/check/abc',
    item_id: str | None = None,
) -> bytes:
    payload: dict = {'success': success}
    if link is not None:
        payload['link'] = link
    if item_id is not None:
        payload['item_id'] = item_id
    return json.dumps(payload).encode()


class TestRawToData:
    def test_valid_json_bytes(self) -> None:
        service = Tax3rCheckProcessor()
        result = service._raw_to_data(b'{"success": true}')
        assert result == {'success': True}

    def test_valid_json_str(self) -> None:
        service = Tax3rCheckProcessor()
        result = service._raw_to_data('{"success": true}')
        assert result == {'success': True}

    def test_invalid_json_returns_none(self) -> None:
        service = Tax3rCheckProcessor()
        assert service._raw_to_data(b'not-json') is None

    def test_non_dict_returns_none(self) -> None:
        service = Tax3rCheckProcessor()
        assert service._raw_to_data(b'[1, 2, 3]') is None


class TestIsSuccessful:
    def test_returns_true_when_success(self) -> None:
        service = Tax3rCheckProcessor()
        assert service._is_successful({'success': True}) is True

    def test_returns_false_when_not_success(self) -> None:
        service = Tax3rCheckProcessor()
        assert service._is_successful({'success': False}) is False

    def test_returns_false_when_missing(self) -> None:
        service = Tax3rCheckProcessor()
        assert service._is_successful({}) is False


class TestGetLink:
    def test_returns_link(self) -> None:
        service = Tax3rCheckProcessor()
        assert service._get_link({'link': 'https://example.com'}) == 'https://example.com'

    def test_returns_none_when_missing(self) -> None:
        service = Tax3rCheckProcessor()
        assert service._get_link({}) is None

    def test_returns_none_when_empty(self) -> None:
        service = Tax3rCheckProcessor()
        assert service._get_link({'link': ''}) is None


class TestGetItemId:
    def test_returns_string(self) -> None:
        service = Tax3rCheckProcessor()
        item_id = str(uuid.uuid4())
        assert service._get_item_id({'item_id': item_id}) == item_id

    def test_returns_none_when_missing(self) -> None:
        service = Tax3rCheckProcessor()
        assert service._get_item_id({}) is None


class TestAct:
    def test_empty_queue_returns_zero(
        self,
        mock_lpop: MockType,
        payment_ready_for_check: Payment,
    ) -> None:
        mock_lpop.return_value = None
        count = Tax3rCheckProcessor()()
        assert count == 0
        payment_ready_for_check.refresh_from_db()
        assert not payment_ready_for_check.is_check_sent

    def test_successful_entry_updates_payment(
        self,
        mock_lpop: MockType,
        mock_notification_sender: MockType,
        payment_ready_for_check: Payment,
    ) -> None:
        check_link = 'https://tax3r.example.com/check/xyz'
        mock_lpop.side_effect = [
            _make_raw(success=True, link=check_link, item_id=str(payment_ready_for_check.pk)),
            None,
        ]
        count = Tax3rCheckProcessor()()
        assert count == 1
        payment_ready_for_check.refresh_from_db()
        assert payment_ready_for_check.is_check_sent is True
        assert payment_ready_for_check.check_url == check_link

    def test_successful_entry_sends_notification(
        self,
        mock_lpop: MockType,
        mock_notification_sender: MockType,
        payment_ready_for_check: Payment,
    ) -> None:
        mock_lpop.side_effect = [
            _make_raw(
                success=True, link='https://tax3r.example.com/check/xyz', item_id=str(payment_ready_for_check.pk)
            ),
            None,
        ]
        Tax3rCheckProcessor()()
        mock_notification_sender.assert_called_once()

    def test_unsuccessful_entry_skips_payment(
        self,
        mock_lpop: MockType,
        mock_notification_sender: MockType,
        payment_ready_for_check: Payment,
    ) -> None:
        mock_lpop.side_effect = [
            _make_raw(
                success=False, link='https://tax3r.example.com/check/xyz', item_id=str(payment_ready_for_check.pk)
            ),
            None,
        ]
        count = Tax3rCheckProcessor()()
        assert count == 1
        payment_ready_for_check.refresh_from_db()
        assert not payment_ready_for_check.is_check_sent
        mock_notification_sender.assert_not_called()

    def test_missing_link_skips_payment(
        self,
        mock_lpop: MockType,
        mock_notification_sender: MockType,
        payment_ready_for_check: Payment,
    ) -> None:
        payload = json.dumps({'success': True, 'item_id': str(payment_ready_for_check.pk)}).encode()
        mock_lpop.side_effect = [payload, None]
        count = Tax3rCheckProcessor()()
        assert count == 1
        payment_ready_for_check.refresh_from_db()
        assert not payment_ready_for_check.is_check_sent
        mock_notification_sender.assert_not_called()

    def test_missing_item_id_skips_payment(
        self,
        mock_lpop: MockType,
        mock_notification_sender: MockType,
        payment_ready_for_check: Payment,
    ) -> None:
        payload = json.dumps({'success': True, 'link': 'https://tax3r.example.com/check/xyz'}).encode()
        mock_lpop.side_effect = [payload, None]
        count = Tax3rCheckProcessor()()
        assert count == 1
        payment_ready_for_check.refresh_from_db()
        assert not payment_ready_for_check.is_check_sent
        mock_notification_sender.assert_not_called()

    def test_unknown_payment_id_skips(
        self,
        mock_lpop: MockType,
        mock_notification_sender: MockType,
    ) -> None:
        unknown_id = str(uuid.uuid4())
        mock_lpop.side_effect = [
            _make_raw(success=True, link='https://tax3r.example.com/check/xyz', item_id=unknown_id),
            None,
        ]
        count = Tax3rCheckProcessor()()
        assert count == 1
        mock_notification_sender.assert_not_called()

    def test_multiple_entries_processed(
        self,
        mock_lpop: MockType,
        mock_notification_sender: MockType,
        payment_ready_for_check: Payment,
    ) -> None:
        link = 'https://tax3r.example.com/check/xyz'
        item_id = str(payment_ready_for_check.pk)
        # Three entries: first valid, second unknown id, third success=False — all counted
        mock_lpop.side_effect = [
            _make_raw(success=True, link=link, item_id=item_id),
            _make_raw(success=True, link=link, item_id=str(uuid.uuid4())),
            _make_raw(success=False, link=link, item_id=item_id),
            None,
        ]
        count = Tax3rCheckProcessor()()
        assert count == 3


class TestCeleryTask:
    def test_task_calls_service(self, mocker: MockFixture) -> None:
        mock_act = mocker.patch.object(Tax3rCheckProcessorTaskService, '__call__', return_value=0)
        result = process_tax3r_check_results()
        mock_act.assert_called_once()
        assert 'Processed' in result
