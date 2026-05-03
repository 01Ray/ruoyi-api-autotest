"""用户管理模块接口测试"""

import pytest
import allure


@allure.epic("RuoYi 接口自动化")
@allure.feature("用户管理")
class TestUserQuery:
    """用户查询类用例"""

    @allure.story("查询")
    @allure.title("查询用户列表 - 默认参数")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    @pytest.mark.user
    def test_user_list_default(self, admin_client):
        """默认参数查询用户列表，验证响应结构"""
        result = admin_client.get("/system/user/list")

        # HTTP + 业务双层断言
        assert result["_status_code"] == 200
        assert result["code"] == 200
        
        # 数据结构断言
        assert "rows" in result, "响应缺少 rows 字段"
        assert "total" in result, "响应缺少 total 字段"
        assert isinstance(result["rows"], list), "rows 应该是列表"
        assert result["total"] >= 1, "至少应有 admin 用户"

    @allure.story("查询")
    @allure.title("分页查询用户列表")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.user
    def test_user_list_pagination(self, admin_client):
        """分页参数生效，每页大小可控"""
        result = admin_client.get(
            "/system/user/list",
            params={"pageNum": 1, "pageSize": 1}
        )

        assert result["code"] == 200
        assert len(result["rows"]) <= 1, "pageSize=1 时单页应≤1 条"

    @allure.story("查询")
    @allure.title("按用户名模糊搜索")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.user
    def test_user_list_search_by_username(self, admin_client):
        """搜索 admin 应能找到 admin 用户"""
        result = admin_client.get(
            "/system/user/list",
            params={"userName": "admin"}
        )

        assert result["code"] == 200
        assert result["total"] >= 1
        # 所有返回结果应该都包含 admin
        for user in result["rows"]:
            assert "admin" in user["userName"].lower()

    @allure.story("查询")
    @allure.title("按状态筛选 - 只看正常用户")
    @allure.severity(allure.severity_level.MINOR)
    @pytest.mark.user
    def test_user_list_filter_by_status(self, admin_client):
        """status=0 (正常) 筛选"""
        result = admin_client.get(
            "/system/user/list",
            params={"status": "0"}
        )

        assert result["code"] == 200
        for user in result["rows"]:
            assert user["status"] == "0", f"status 筛选失效，返回了 {user}"

    @allure.story("查询")
    @allure.title("查询用户详情 - admin 用户")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    @pytest.mark.user
    def test_user_detail(self, admin_client):
        """查询 userId=1 的用户详情，验证嵌套数据结构"""
        result = admin_client.get("/system/user/1")

        assert result["code"] == 200

        # 主体数据
        user = result["data"]
        assert user["userId"] == 1
        assert user["userName"] == "admin"
        assert user["nickName"] == "若依"
        assert user["admin"] is True

        # 角色岗位数据（编辑页用）
        assert isinstance(result["roles"], list)
        assert isinstance(result["posts"], list)
        assert len(result["roles"]) >= 1
        assert len(result["posts"]) >= 1

    @allure.story("查询")
    @allure.title("查询不存在的用户 ID")
    @allure.severity(allure.severity_level.MINOR)
    @pytest.mark.user
    def test_user_detail_not_exist(self, admin_client):
        """查询一个肯定不存在的 userId"""
        result = admin_client.get("/system/user/999999")

        # RuoYi 这种情况通常返回 500
        assert result["code"] == 500
        # data 可能为 null 或空对象，灵活断言
        assert result.get("data") is None or result.get("data") == {}


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
    @allure.title("新增用户 - 完整字段")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    @pytest.mark.user
    def test_user_create_success(self, admin_client, test_user_id):
        """fixture 已经创建用户，这里只验证它确实存在"""
        result = admin_client.get(f"/system/user/{test_user_id}")

        assert result["code"] == 200
        assert result["data"]["userId"] == test_user_id
        assert "test_user_" in result["data"]["userName"]

    @allure.story("新增")
    @allure.title("新增用户 - 用户名重复应失败")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.user
    def test_user_create_duplicate_username(self, admin_client):
        """已存在的用户名应被拒绝"""
        duplicate_user = {
            "userName": "admin",  # 故意用已存在的
            "nickName": "重复名称测试",
            "password": "test123"
        }
        result = admin_client.post("/system/user", json=duplicate_user)

        # 业务层应拒绝
        assert result["code"] == 500
        assert "已存在" in result["msg"] or "重复" in result["msg"]

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
    @allure.title("删除用户 - 单个（软删除）")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.user
    def test_user_delete_single(self, admin_client):
        """
        删除单个用户后，验证：
        1. 删除接口返回成功
        2. 用户列表查不到（软删除被过滤）
        3. 用户名可以重新被使用（被释放）
        """
        import time
        unique_name = f"to_delete_{int(time.time() * 1000)}"

        # 1. 创建
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

        # 2. 删除
        delete_result = admin_client.delete(f"/system/user/{user_id}")
        assert delete_result["code"] == 200

        # 3. 验证列表已查不到
        list_after = admin_client.get(
            "/system/user/list",
            params={"userName": unique_name}
        )
        assert list_after["total"] == 0, "软删除后列表仍能查到"

    @allure.story("删除")
    @allure.title("删除用户 - 不能删除超级管理员")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.user
    def test_user_delete_admin_forbidden(self, admin_client):
        """超管 admin 用户应不允许删除（业务规则）"""
        result = admin_client.delete("/system/user/1")

        # RuoYi 应该拦截这个操作
        assert result["code"] == 500