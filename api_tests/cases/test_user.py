"""用户管理模块接口测试"""

import time
import pytest
import allure


@allure.epic("RuoYi 接口自动化")
@allure.feature("用户管理")
class TestUserCRUD:
    """用户增删改用例"""

    @pytest.fixture
    def test_user_id(self, admin_client):
        """
        创建测试用户的 fixture，用例结束后自动删除
        
        通过 yield 实现 setup/teardown 模式：
        - yield 之前的代码 = 用例执行前（创建用户）
        - yield 返回的值 = 用例可用的数据（user_id）
        - yield 之后的代码 = 用例执行后（清理用户）
        """
        # === setup：创建测试用户 ===
        import time
        unique_name = f"test_user_{int(time.time() * 1000)}"  # 时间戳保证唯一

        new_user = {
            "userName": unique_name,
            "nickName": "自动化测试",
            "password": "test123",
            "phonenumber": "13900000000",
            "email": "test@auto.com",
            "sex": "0",
            "status": "0",
            "deptId": 103,
            "roleIds": [2],
            "postIds": [4],
            "remark": "自动化创建，可删除"
        }
        result = admin_client.post("/system/user", json=new_user)
        assert result["code"] == 200, f"前置创建用户失败: {result['msg']}"

        # 查询刚创建的 userId
        list_result = admin_client.get(
            "/system/user/list",
            params={"userName": unique_name}
        )
        user_id = list_result["rows"][0]["userId"]

        yield user_id  # 把 userId 给用例用

        # === teardown：清理 ===
        admin_client.delete(f"/system/user/{user_id}")

    @allure.story("新增")
    @allure.title("新增用户 - 完整字段（含数据库落地验证）")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    @pytest.mark.user
    def test_user_create_success(self, admin_client, test_user_id, db_client):
        """
        创建用户后，验证：
        1. 接口能查到新用户（fixture 已经做了）
        2. 接口字段与数据库一致
        3. delFlag = '0' 表示数据正常落库（不是软删除状态）
        """
        # === 验证接口层 ===
        result = admin_client.get(f"/system/user/{test_user_id}")
        assert result["code"] == 200
        api_user = result["data"]

        # === 验证数据库层（端到端断言）===
        with allure.step("数据库验证：用户记录已写入 sys_user 表"):
            db_user = db_client.fetch_one(
                "SELECT user_name, nick_name, status, del_flag, dept_id "
                "FROM sys_user WHERE user_id = %s",
                (test_user_id,)
            )

            # 数据库里有这条记录
            assert db_user is not None, f"用户 ID {test_user_id} 在数据库中不存在"

            # 接口数据 vs 数据库数据一致
            assert api_user["userName"] == db_user["user_name"]
            assert api_user["nickName"] == db_user["nick_name"]
            assert api_user["status"] == db_user["status"]

            # 数据状态正常（未被软删除）
            assert db_user["del_flag"] == "0", \
                f"新建用户 del_flag 应为 '0'，实际 '{db_user['del_flag']}'"

    @allure.story("修改")
    @allure.title("修改用户 - 修改昵称")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.user
    def test_user_update_nickname(self, admin_client, test_user_id):
        """修改用户昵称：先查再改（避免缺字段被服务端拒绝）"""
        # 1. 查出完整数据
        detail = admin_client.get(f"/system/user/{test_user_id}")
        user_data = detail["data"]
        
        # 2. 改字段
        user_data["nickName"] = "修改后的昵称"
        # 必须额外带上 roleIds 和 postIds（编辑页设计）
        user_data["roleIds"] = detail.get("roleIds", [])
        user_data["postIds"] = detail.get("postIds", [])
        
        # 3. PUT 提交完整对象
        update_result = admin_client.put("/system/user", json=user_data)
        assert update_result["code"] == 200, f"修改失败: {update_result['msg']}"

        # 4. 二次查询验证
        verify = admin_client.get(f"/system/user/{test_user_id}")
        assert verify["data"]["nickName"] == "修改后的昵称"

    @allure.story("修改")
    @allure.title("修改用户状态 - 停用")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.user
    def test_user_change_status(self, admin_client, test_user_id):
        """修改用户状态为停用"""
        result = admin_client.put(
            "/system/user/changeStatus",
            json={"userId": test_user_id, "status": "1"}
        )
        assert result["code"] == 200

        # 验证状态改了
        verify = admin_client.get(f"/system/user/{test_user_id}")
        assert verify["data"]["status"] == "1"

    @allure.story("删除")
    @allure.title("删除用户 - 软删除验证（接口 + 数据库双层）")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.user
    def test_user_delete_single(self, admin_client, db_client):
        """
        软删除验证：
        - 接口层：列表查不到
        - 数据库层：del_flag 从 '0' 变成 '2'
        """
        unique_name = f"to_delete_{int(time.time() * 1000)}"

        # 创建
        admin_client.post("/system/user", json={
            "userName": unique_name,
            "nickName": "待删除",
            "password": "test123"
        })
        list_r = admin_client.get(
            "/system/user/list",
            params={"userName": unique_name}
        )
        user_id = list_r["rows"][0]["userId"]

        # 删除前 - 验证数据库 del_flag = '0'
        with allure.step("删除前：del_flag = '0'"):
            before = db_client.fetch_one(
                "SELECT del_flag FROM sys_user WHERE user_id = %s",
                (user_id,)
            )
            assert before["del_flag"] == "0"

        # 执行删除
        delete_result = admin_client.delete(f"/system/user/{user_id}")
        assert delete_result["code"] == 200

        # 删除后 - 接口层验证
        with allure.step("接口层验证：列表查不到"):
            list_after = admin_client.get(
                "/system/user/list",
                params={"userName": unique_name}
            )
            assert list_after["total"] == 0

        # 删除后 - 数据库层验证
        with allure.step("数据库层验证：del_flag = '2'（软删除标记）"):
            after = db_client.fetch_one(
                "SELECT del_flag FROM sys_user WHERE user_id = %s",
                (user_id,)
            )
            assert after is not None, "记录应该还在数据库（软删除不真删）"
            assert after["del_flag"] == "2", \
                f"软删除后 del_flag 应为 '2'，实际 '{after['del_flag']}'"

    @allure.story("删除")
    @allure.title("删除用户 - 不能删除超级管理员")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.user
    def test_user_delete_admin_forbidden(self, admin_client):
        """超管 admin 用户应不允许删除（业务规则）"""
        result = admin_client.delete("/system/user/1")

        # RuoYi 应该拦截这个操作
        assert result["code"] == 500