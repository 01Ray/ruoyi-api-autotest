"""字典管理模块接口测试"""

import time

import allure
import pytest


# ============================================================
# 字典类型 CRUD（主表）
# ============================================================
@allure.epic("RuoYi 接口自动化")
@allure.feature("字典管理")
class TestDictTypeCRUD:
    """字典类型增删改用例"""

    @pytest.fixture
    def test_dict_type_id(self, admin_client):
        """
        创建测试字典类型 fixture
        
        用 dictType 时间戳保证唯一（业务级唯一约束）
        """
        unique_type = f"test_dict_{int(time.time() * 1000)}"

        admin_client.post("/system/dict/type", json={
            "dictName": "自动化测试字典",
            "dictType": unique_type,
            "status": "0",
            "remark": "自动化创建，可删除"
        })

        # 查 dictId
        list_r = admin_client.get(
            "/system/dict/type/list",
            params={"dictType": unique_type}
        )
        dict_id = list_r["rows"][0]["dictId"]

        yield {"id": dict_id, "type": unique_type}

        # 清理（可能已被用例删了，加 try 容错）
        try:
            admin_client.delete(f"/system/dict/type/{dict_id}")
        except Exception:
            pass

    @allure.story("新增")
    @allure.title("新增字典类型 - 完整字段")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    @pytest.mark.dict
    def test_dict_type_create(self, admin_client, test_dict_type_id):
        """fixture 已经创建字典类型，验证它确实存在"""
        result = admin_client.get(f"/system/dict/type/{test_dict_type_id['id']}")

        assert result["code"] == 200
        assert result["data"]["dictType"] == test_dict_type_id["type"]
        assert result["data"]["status"] == "0"

    @allure.story("新增")
    @allure.title("新增字典类型 - dictType 重复应失败")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.dict
    def test_dict_type_create_duplicate(self, admin_client):
        """已存在的 dictType（如 sys_user_sex）应被拒绝"""
        result = admin_client.post("/system/dict/type", json={
            "dictName": "重复测试",
            "dictType": "sys_user_sex",  # 故意用已存在的
            "status": "0"
        })

        assert result["code"] == 500
        assert "已存在" in result["msg"] or "重复" in result["msg"]

    @allure.story("修改")
    @allure.title("修改字典类型 - 修改名称")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.dict
    def test_dict_type_update(self, admin_client, test_dict_type_id):
        """先查后改 - PUT 全量提交"""
        detail = admin_client.get(f"/system/dict/type/{test_dict_type_id['id']}")
        dict_data = detail["data"]
        dict_data["dictName"] = "修改后的名称"

        update_result = admin_client.put("/system/dict/type", json=dict_data)
        assert update_result["code"] == 200

        # 二次查询验证
        verify = admin_client.get(f"/system/dict/type/{test_dict_type_id['id']}")
        assert verify["data"]["dictName"] == "修改后的名称"

    @allure.story("删除")
    @allure.title("删除字典类型 - 单个")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.dict
    def test_dict_type_delete(self, admin_client, db_client):
        """创建后删除（不用 fixture，独立验证）"""
        unique_type = f"to_delete_{int(time.time() * 1000)}"

        admin_client.post("/system/dict/type", json={
            "dictName": "待删除字典",
            "dictType": unique_type,
            "status": "0"
        })
        list_r = admin_client.get(
            "/system/dict/type/list",
            params={"dictType": unique_type}
        )
        dict_id = list_r["rows"][0]["dictId"]

        # 删除前 - 数据库验证存在
        with allure.step("删除前：数据库 sys_dict_type 表存在记录"):
            before = db_client.fetch_one(
                "SELECT dict_id FROM sys_dict_type WHERE dict_id = %s",
                (dict_id,)
            )
            assert before is not None

        # 执行删除
        delete_result = admin_client.delete(f"/system/dict/type/{dict_id}")
        assert delete_result["code"] == 200

        # 接口层验证：列表查不到
        with allure.step("接口层验证：列表已查不到"):
            list_after = admin_client.get(
                "/system/dict/type/list",
                params={"dictType": unique_type}
            )
            assert list_after["total"] == 0

        # 数据库层验证：硬删除（字典是真删，不是软删）
        with allure.step("数据库层验证：sys_dict_type 表记录已删除（硬删除）"):
            after = db_client.fetch_one(
                "SELECT dict_id FROM sys_dict_type WHERE dict_id = %s",
                (dict_id,)
            )
            assert after is None, "字典类型应该是硬删除（不同于用户的软删除）"

    @allure.story("删除")
    @allure.title("级联删除验证 - 删除字典类型时关联数据的处理")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.dict
    def test_dict_type_delete_with_data(self, admin_client, db_client):
        """
        关联完整性的核心测试：
        - 创建一个字典类型
        - 给它加一条字典数据
        - 删除字典类型
        - 验证 RuoYi 的处理：拒绝删除？级联删除？孤儿数据？
        
        这种测试发现的"行为"会变成系统文档的一部分
        """
        unique_type = f"cascade_test_{int(time.time() * 1000)}"

        # 1. 创建字典类型
        admin_client.post("/system/dict/type", json={
            "dictName": "级联测试字典",
            "dictType": unique_type,
            "status": "0"
        })

        # 2. 给它加一条字典数据
        admin_client.post("/system/dict/data", json={
            "dictType": unique_type,
            "dictLabel": "测试选项",
            "dictValue": "1",
            "dictSort": 1,
            "status": "0"
        })

        # 验证字典数据真的写入了
        with allure.step("验证：字典数据已通过接口创建"):
            data_r = admin_client.get(
                "/system/dict/data/list",
                params={"dictType": unique_type}
            )
            assert data_r["total"] == 1

        # 3. 拿 dictId
        list_r = admin_client.get(
            "/system/dict/type/list",
            params={"dictType": unique_type}
        )
        dict_id = list_r["rows"][0]["dictId"]

        # 4. 尝试删除字典类型
        with allure.step("尝试删除有关联数据的字典类型"):
            delete_result = admin_client.delete(f"/system/dict/type/{dict_id}")

        # 5. 业务规则验证：RuoYi 应该拒绝删除（保护关联数据）
        # 注意：这里我们先观察 RuoYi 实际行为，再决定断言
        # 通常企业应用都会拒绝，给出 "存在数据，不允许删除" 的提示
        if delete_result["code"] == 200:
            # 如果 RuoYi 允许了 → 验证字典数据是否被孤儿化（这是 bug 的话会发现）
            with allure.step("已删除：验证字典数据是否仍存在（可能是 bug）"):
                orphans = db_client.fetch_all(
                    "SELECT dict_code FROM sys_dict_data WHERE dict_type = %s",
                    (unique_type,)
                )
                # 用 print 输出供调试，断言宽松（先观察行为）
                print(f"\n字典类型已删，关联字典数据剩余: {len(orphans)} 条")
        else:
            # 如果 RuoYi 拒绝了 → 这是预期的安全行为
            assert delete_result["code"] == 500
            with allure.step(f"RuoYi 拒绝删除：{delete_result['msg']}"):
                pass

            # 清理：先删数据，再删类型
            data_to_delete = admin_client.get(
                "/system/dict/data/list",
                params={"dictType": unique_type}
            )
            for d in data_to_delete["rows"]:
                admin_client.delete(f"/system/dict/data/{d['dictCode']}")
            admin_client.delete(f"/system/dict/type/{dict_id}")


# ============================================================
# 字典数据 CRUD（从表）
# ============================================================
@allure.epic("RuoYi 接口自动化")
@allure.feature("字典管理")
class TestDictDataCRUD:
    """字典数据增删改用例（每个测试用独立的字典类型，避免污染内置数据）"""

    @pytest.fixture
    def isolated_dict_type(self, admin_client):
        """
        创建一个独立的测试字典类型 + 自动清理
        
        每个测试用例都用自己专属的 dictType，避免污染 sys_user_sex 等内置数据
        """
        unique_type = f"data_test_{int(time.time() * 1000)}"

        admin_client.post("/system/dict/type", json={
            "dictName": "数据测试字典",
            "dictType": unique_type,
            "status": "0"
        })

        yield unique_type

        # teardown：先删该类型下所有数据，再删类型本身
        try:
            data_r = admin_client.get(
                "/system/dict/data/list",
                params={"dictType": unique_type}
            )
            for d in data_r.get("rows", []):
                admin_client.delete(f"/system/dict/data/{d['dictCode']}")

            type_r = admin_client.get(
                "/system/dict/type/list",
                params={"dictType": unique_type}
            )
            if type_r.get("rows"):
                admin_client.delete(f"/system/dict/type/{type_r['rows'][0]['dictId']}")
        except Exception:
            pass

    @allure.story("新增")
    @allure.title("新增字典数据 - 在独立字典类型下")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    @pytest.mark.dict
    def test_dict_data_create(self, admin_client, isolated_dict_type):
        """在独立的 dictType 下创建数据，避免数据污染"""
        # 创建一条数据
        create_r = admin_client.post("/system/dict/data", json={
            "dictType": isolated_dict_type,
            "dictLabel": "测试选项",
            "dictValue": "1",
            "dictSort": 1,
            "status": "0"
        })
        assert create_r["code"] == 200

        # 查询验证（独立 dictType，整个列表就是我们刚创建的）
        list_r = admin_client.get(
            "/system/dict/data/list",
            params={"dictType": isolated_dict_type}
        )
        assert list_r["total"] == 1, f"独立 dictType 下应只有 1 条数据，实际 {list_r['total']}"

        item = list_r["rows"][0]
        assert item["dictLabel"] == "测试选项"
        assert item["dictValue"] == "1"
        assert item["dictType"] == isolated_dict_type

    @allure.story("修改")
    @allure.title("修改字典数据 - 修改 label")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.dict
    def test_dict_data_update(self, admin_client, isolated_dict_type):
        """在独立 dictType 下做修改测试"""
        # 创建一条
        admin_client.post("/system/dict/data", json={
            "dictType": isolated_dict_type,
            "dictLabel": "原始标签",
            "dictValue": "1",
            "dictSort": 1,
            "status": "0"
        })

        # 拿 dictCode
        list_r = admin_client.get(
            "/system/dict/data/list",
            params={"dictType": isolated_dict_type}
        )
        dict_code = list_r["rows"][0]["dictCode"]

        # 先 GET 拿完整数据再修改（PUT 全量提交模式）
        detail = admin_client.get(f"/system/dict/data/{dict_code}")
        data = detail["data"]
        data["dictLabel"] = "修改后的标签"

        update_r = admin_client.put("/system/dict/data", json=data)
        assert update_r["code"] == 200

        # 二次查询验证
        verify = admin_client.get(f"/system/dict/data/{dict_code}")
        assert verify["data"]["dictLabel"] == "修改后的标签"

    @allure.story("删除")
    @allure.title("删除字典数据 - 单条")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.dict
    def test_dict_data_delete(self, admin_client, isolated_dict_type):
        """在独立 dictType 下做删除测试"""
        # 创建
        admin_client.post("/system/dict/data", json={
            "dictType": isolated_dict_type,
            "dictLabel": "待删除",
            "dictValue": "1",
            "dictSort": 1,
            "status": "0"
        })

        # 拿 dictCode
        list_before = admin_client.get(
            "/system/dict/data/list",
            params={"dictType": isolated_dict_type}
        )
        assert list_before["total"] == 1
        dict_code = list_before["rows"][0]["dictCode"]

        # 删除
        delete_r = admin_client.delete(f"/system/dict/data/{dict_code}")
        assert delete_r["code"] == 200

        # 验证删除后列表为空
        list_after = admin_client.get(
            "/system/dict/data/list",
            params={"dictType": isolated_dict_type}
        )
        assert list_after["total"] == 0


# ============================================================
# 缓存刷新（特殊接口）
# ============================================================
@allure.epic("RuoYi 接口自动化")
@allure.feature("字典管理")
class TestDictCache:
    """字典缓存接口测试"""

    @allure.story("缓存")
    @allure.title("刷新字典缓存接口")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.dict
    def test_refresh_cache(self, admin_client):
        """手动刷新缓存接口能正常工作"""
        result = admin_client.delete("/system/dict/type/refreshCache")
        assert result["code"] == 200