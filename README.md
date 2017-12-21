# Resource Usage Monitor

프로세스 별 컴퓨터 자원 사용률을 확인하여 과부하를 일으키는 프로세스를 확인하는 스크립트

## 1. 동작 원리

### 1) 사용률
- CPU 사용률 : 0.1초를 기준으로 시스템 CPU 동작 시간과 프로세스 CPU 사용 시간을 비교하여 프로세스 별 CPU 사용률을 계산합니다. (멀티코어 환경에서 다중 스레드 작업을 하는 프로세스의 경우 100.0을 초과할 수 있습니다.) 또한 CPU 리소스를 늘리는 프로세스를 쉽게 식별하기 위해서 CPU 수를 고려하지않고 계산하고 있습니다. 예를 들어 2개의 논리 CPU로 구성된 시스템에서 실행 중인 루프 프로세스가 있다면 50%가 아닌 100%로 계산합니다. (윈도우즈의 taskmgr.exe는 이렇게 구한 CPU 사용률에서 CPU 수를 나눠서 결과를 출력하여 50%가 출력됩니다.)

- 메모리 사용률 : 프로세스 메모리와 전체 물리 시스템 메모리를 비교하여 프로세스 메모리 사용률을 구합니다.

### 2) 동작 흐름
1. 현재 시스템 내 동작 프로세스 PID 수집
2. 프로세스 정보 수집 스레드 생성
3. PID 별 CPU 사용률, 메모리 사용률, 읽기/쓰기 횟수, 읽기/쓰기 바이트 수집
4. 수집 정보 sqlite(메모리 타입) 데이터베이스 저장 스레드 생성하여 저장
5. 설정된 총 수집 시간 동안 interval 값에 맞춰 대기 후 수집 작업 재 수행
6. 수집 시간 종료 후 sqlite(메모리 타입) 데이터 베이스 수집 데이터 덤프 생성
7. sqlite(메모리 타입) 데이터 베이스 연결 종료
8. 덤프 파일을 이용하여 sqlite 물리 데이터 베이스 파일 생성
9. sqlite 물리 데이터 베이스 파일에서 전체 값 읽어와 CSV 파일 생성
10. sqlite 물리 데이터 베이스 파일에서 항목 별 순위 값 불러와 엑셀 파일 생성
11.프로그램 종료

## 2. 클래스
- DocumentManager : csv, excel 문서 생성 클래스
- AnalysisManager : 수집 데이터 처리 클래스
- CollectManager : 수집 데이터 저장 클래스
- ProcessManager : 프로세스 데이터 수집 클래스
- Secretary : 프로그램 전체 로직 관리 클래스

## 3. 메서드
### 1) DocumentManager
- create_csv : 전체 수집 데이터를 csv 파일로 생성
- create_xl : 엑셀 생성 로직 관리 
- set_format : excel 포맷 지정
- set_title : 제목 생성
- set_index : 줄번호 생성
- set_cpu_percent_rank : CPU 사용률 항목 상위 15개 삽입
- get_cpu_percent_rank : CPU 사용률 항목 상위 15개 데이터 읽어오기
- set_memory_rank : 메모리 사용률 항목 상위 15개 삽입
- get_memory_rank : 메모리 사용률 항목 상위 15개 데이터 읽어오기
- set_read_rank : 디스크 읽기 횟수 항목 상위 15개 삽입
- get_read_rank : 디스크 읽기 횟수 항목 상위 15개 데이터 읽어오기
- set_write_rank : 디스크 쓰기 횟수 항목 상위 15개 삽입
- get_write_rank : 디스크 쓰기 횟수 항목 상위 15개 데이터 읽어오기
- write_data : 엑셀에 데이터 삽입

### 2) AnalysisManager
- _connect_process_data : 물리 데이터 베이스 연결
- _check_database : 덤프 파일 존재 확인
- execute : 쿼리 실행 및 결과 반환
- create_database : 덤파 파일을 이용하여 물리 데이터 베이스 생성
- get_write_count_rank : 디스크 쓰기 횟수 항목 상위 15개 데이터 읽어오는 쿼리 수행
- get_read_count_rank : 디스크 읽기 횟수 항목 상위 15개 데이터 읽어오는 쿼리 수행
- get_cpu_percent_rank : CPU 사용률 항목 상위 15개 데이터 읽어오는 쿼리 수행
- get_memory_rank : 메모리 사용률 항목 상위 15개 데이터 읽어오는 쿼리 수행
- get_all_data : 전체 데이터 읽어오는 쿼리 수행

### 3) CollectManager
- create_table : 테이블 생성
- set_process_data : 수집 데이터 삽입
- classify : 수집 데이터 분류
- dump : 수집 데이터 덤프 파일 생성
- working : 데어터 저장 로직 관리

### 4) ProcessManager
- get_name : 프로세스 명 추출
- get_cpu_percent : CPU 사용률 추출
- get_cpu_times : CPU 사용 시간 추출
- get_memory : 메모리 사용률 추출
- get_disk_io : 디스크 읽기/쓰기 데이터 추출
- get_summary : 추출 데이터 병합
- working : 프로세스 데이터 추출 로직 관리

### 5) Secretary
- _check_interval_time : 수집 시간 간격 확인 
- checked_limit_time : 수집 시간 확인
- get_pids : 현재 시스템 내 동작 중인 프로세스들의 PID 목록 추출
- get_process_data : 추출한 PID를 이용한 프로세스 데이터 추출
- save_monitor_data : 추출한 프로세스 데이터 저장
- monitor_work : 프로세스 데이터 추출 스레드 생성
- save_work : 추출 데이터 저장 스레드 생성
- write_document : CSV, Excel 파일 생성
- delete_dump : 덤프 파일 삭제
- process_monitoring : 프로세스 데이터 추출 및 저장 로직 관리
- debug : 진행 상황 커맨드 라인에 출력
- start : 프로그램 전체 로직 관리

### 6) main
- 인자 값 관리
